""" A web app to automate build and deployment of static sites on GitHub. """

# Standard library.
import base64
from functools import wraps
import json
import logging
from logging.handlers import RotatingFileHandler
from os.path import abspath, dirname, exists, join
import re
import yaml

# 3rd party library.
from flask import (
    flash, Flask, jsonify, redirect, render_template, request, url_for
)
from flask_login import (
    current_user, LoginManager, login_user, login_required, logout_user,
    UserMixin
)
from flask_sqlalchemy import SQLAlchemy
from markdown import markdown
from rauth.service import OAuth2Service
import requests
import rsa

AUTHORIZE_URL = 'https://github.com/login/oauth/authorize'
SCRIPT = 'travis_build_n_deploy.sh'
HERE = dirname(abspath(__file__))
SITE = 'Statiki'
DESCRIPTION = 'An easy-to-use service for deploying simple web-sites'


# Flask setup
app = Flask(__name__)
if exists(join(HERE, 'settings.py')):
    path = join(HERE, 'settings.py')
else:
    path = join(HERE, 'sample-settings.py')
app.config.from_pyfile(path)
db = SQLAlchemy(app)

# Logging setup
if not app.config.get('DEBUG', False):
    formatter = logging.Formatter(
        '[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s'
    )
    handler = RotatingFileHandler(
        app.config['LOG_FILENAME'], maxBytes=10000000, backupCount=5
    )
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.DEBUG)
    log.addHandler(handler)
    app.logger.addHandler(handler)

# Login related
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# rauth OAuth 2.0 service wrapper
github = OAuth2Service(
    client_id=app.config['CLIENT_ID'],
    client_secret=app.config['CLIENT_SECRET'],
    name='github',
    authorize_url=AUTHORIZE_URL,
    access_token_url='https://github.com/login/oauth/access_token',
    base_url='https://api.github.com/'
)


#### decorators ###############################################################

def travis_login_required(func):
    """ Ensures that the view is visible only to a travis user.

    NOTE: Always use along with the login_required decorator, and below it.

    """

    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not is_travis_user(current_user.access_token):
            response = {
                'message': (
                    'Please <a href="https://travis-ci.org/profile" target='
                    '"_blank">signup</a> for a Travis-ci account to proceed.'
                ),
            }
            return jsonify(response)
        return func(*args, **kwargs)
    return decorated_view


#### models ###################################################################

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    gh_id = db.Column(db.String(120))
    access_token = db.Column(db.String(40))

    def __init__(self, username, gh_id):
        self.username = username
        self.gh_id = gh_id

    def __repr__(self):
        return '<User %r>' % self.username

    def set_access_token(self, access_token):
        app.logger.info('Setting access token for %s', self.username)
        self.access_token = access_token
        db.session.commit()

    @staticmethod
    def get_or_create(username, gh_id):
        user = User.query.filter_by(username=username).first()
        if user is None:
            user = User(username, gh_id)
            db.session.add(user)
            db.session.commit()
        return user

    @staticmethod
    def get(user_id):
        return User.query.filter_by(id=user_id).first()


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


#### views ####################################################################

@app.route('/')
def index():
    context = {
        'user': current_user,
        'SITE': SITE,
        'DESCRIPTION': DESCRIPTION,
    }
    return render_template('index.html', **context)


@app.route('/authorized')
def authorized():
    # check to make sure the user authorized the request
    if not 'code' in request.args:
        flash('You did not authorize the request')
        return redirect(url_for('index'))

    # make a request for the access token credentials using code
    redirect_uri = url_for('authorized', _external=True)
    data = dict(code=request.args['code'], redirect_uri=redirect_uri)

    session = github.get_auth_session(data=data)

    # the "me" response
    user = session.get('user').json()

    user_obj = User.get_or_create(user['login'], user['id'])
    user_obj.set_access_token(session.access_token)
    login_user(user_obj)
    app.logger.info('Logged in user %s', user_obj.username)

    return redirect(url_for('index'))


@app.route('/login')
def login():
    redirect_uri = url_for('authorized', _external=True)
    params = {
        'redirect_uri': redirect_uri,
        'scope': 'repo'
    }

    return redirect(github.get_authorize_url(**params))


@app.route('/logout')
@login_required
def logout():
    app.logger.info('Logging out user %s', current_user.username)
    logout_user()
    return redirect(url_for('index'))


@app.route('/manage', methods=['POST'])
@login_required
@travis_login_required
def manage():

    repo_name = request.form.get('repo_name', None)
    full_name = '%s/%s' % (current_user.username, repo_name)
    gh_token  = current_user.access_token

    if not repo_name:
        message = 'Need a valid repository name.',
        return jsonify(dict(message=message))

    # If repo does not exist, create it.
    if not is_valid_repo(full_name):
        app.logger.info('Creating new repository %s', full_name)
        create_new_repository(full_name, gh_token)
        app.logger.info('Created repository %s', full_name)

    # If repo not listed in travis, sync
    repo_id = get_repo_id(full_name)
    if repo_id is None:
        app.logger.info('Repo id for %s is None. Syncing', full_name)
        repo_id = sync_and_get_repo_id(full_name, gh_token)

    if repo_id is None:
        app.logger.info('Repo %s could not be found.', full_name)
        message = (
            'Repo could not be found. Run a sync, <a href='
            '"http://travis-ci.org/profile" target="_blank">manually?</a>'
        )
        return jsonify(dict(message=message))

    enabled = enable_ci_for_repo(repo_id, gh_token)
    created = create_travis_files(full_name, gh_token)

    response = get_user_response(enabled, created)
    response['message'] %= full_name

    return jsonify(response)


@app.route('/readme')
def update_readme():
    # Render the readme, again
    render_readme()
    return render_template('readme.html')


#### Helper functions #########################################################

def commit_to_github(path, content, repo, gh_token):
    """ Commit the given content to the given path in a repository. """

    url = 'repos/%s/contents/%s' % (repo, path)
    url = 'https://api.github.com/' + url

    headers = {
        'Authorization': 'token %s' % gh_token,
        'Content-Type': 'application/json'
    }

    payload = {
        'path': path,
        'message': 'Adding %s (from statiki).' % path,
        'content': base64.standard_b64encode(content),
    }
    app.logger.info('Committing file %s to %s', path, repo)
    response = requests.put(url, data=json.dumps(payload), headers=headers)
    app.logger.info(
        'Commit file request: %s, %s', response.status_code, response.text
    )

    return response.status_code == 201


def create_new_repository(repo, gh_token):
    """ Create a new repository given the name and a token.

    NOTE the token must have 'repo' scope, not just 'public_repo'.

    """

    user, user_type, name = get_user_and_repo(repo)

    url = 'https://api.github.com/user/repos'

    headers = {
        'Authorization': 'token %s' % gh_token,
        'Content-Type': 'application/json'
    }

    payload = {
        'name': name,
        'description': 'Website using Nikola, created from statiki',
        'homepage': 'https://%s.github.io/%s' % (user, name),
        'private': False,
        'has_issues': False,
        'has_wiki': False,
        'has_downloads': False,
    }

    app.logger.info('Creating new repo: %s', repo)
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    app.logger.info(
        'Create new repo: %s, %s', response.status_code, response.text
    )

    return response.status_code == 201


def create_travis_files(repo, gh_token):
    """ Create the files required for Travis CI hooks to work. """

    created = {}

    # Create .travis.yml
    content = get_travis_config_contents(repo, gh_token)
    name    = '.travis.yml'
    created[name] = (
        commit_to_github(name, content, repo, gh_token)
        if not github_path_exists(repo, name) else False
    )

    # Create travis script file
    content = get_travis_script_file_contents(repo)
    name    = SCRIPT
    created[name] = (
        commit_to_github(name, content, repo, gh_token)
        if not github_path_exists(repo, name) else False
    )

    return created


def enable_ci_for_repo(repo_id, gh_token):
    """ Enable the travis hook for the repo with the given id. """

    access_token = get_travis_access_token(gh_token)

    if access_token is None:
        status = False

    else:
        payload = json.dumps(dict(hook=dict(active=True, id=repo_id)))
        headers = {
            'Authorization': 'token %s' % access_token,
            'Content-Type': 'application/json; charset=UTF-8'
        }

        url = 'https://api.travis-ci.org/hooks/%s' % repo_id
        app.logger.info('Enabling CI for %s', repo_id)
        response = requests.put(url, data=payload,  headers=headers)
        app.logger.info(
            'Enabling CI: %s, %s', response.status_code, response.text
        )
        status = response.status_code == 200

    return status


def get_encrypted_text(repo_name, data):
    """ Return encrypted text for the data. """

    public_key = get_travis_public_key(repo_name)
    key = rsa.PublicKey.load_pkcs1_openssl_pem(public_key)
    secure = base64.encodestring(rsa.encrypt(data, key))
    secure, _ = re.subn('\s+', '', secure)

    return secure


def get_repo_id(repo):
    """ Get the id for a repo. """

    url      = 'https://api.travis-ci.org/repos/%s' % repo
    response = requests.get(url).json()

    return response.get('id')


def get_travis_access_token(gh_token):

    url = 'https://api.travis-ci.org/auth/github'
    data = {'github_token': gh_token}

    app.logger.info('Getting access_token')
    return requests.post(url, data=data).json().get('access_token')


def get_travis_config_contents(repo, gh_token):
    """ Get the contents to be dumped into the travis config. """

    data = 'GH_TOKEN=%s GIT_NAME=%s GIT_EMAIL=%s' % (
        gh_token.encode(), 'Travis CI', 'testing@travis-ci.org'
    )
    secure = get_encrypted_text(repo, data)

    config = {
        'env': {'global': {'secure': secure}},
        'before_install': 'sudo apt-get install -qq python-lxml',
        'install': 'pip install nikola webassets',
        'branches': {'only': ['master']},
        'language': 'python',
        'python': ['2.7'],
        'script': 'bash %s' % SCRIPT,
        'virtualenv': {'system_site_packages': True},
    }

    return yaml.dump(config)


def get_travis_script_file_contents(repo):
    """ Get the contents of the script file to be run on travis. """

    template = join(dirname(__file__), 'utils', 'travis_script_template.sh')
    with open(template) as f:
        contents = f.read()

    return contents % {'REPO': repo}


def get_travis_public_key(repo):
    """ Get a public key for the repository from travis. """

    url = 'https://api.travis-ci.org/repos/%s' % repo
    response = requests.get(url)
    app.logger.info('Getting travis public key for %s', repo)

    return response.json()['public_key'].replace('RSA PUBLIC', 'PUBLIC')


def get_user_and_repo(repo):
    """ Given <user>/<repo-name> return (username, user_type, repo).

    user_type is one of User or Organization.

    """

    user, name = repo.split('/')
    response = requests.get('https://api.github.com/users/%s' % user)

    user_type = response.json()['type']

    return user, user_type, name


def get_user_response(enabled, created):
    """ Return the response for the user, based on enabled and created. """

    hook_success = 'Successfully enabled publish hook for %s'
    hook_failure = 'Failed to enable publish hooks for %s'
    create_fail  = ', failed to publish: %s'

    if enabled and all(created.values()):
        message = 'Successfully enabled publishing for %s'
        success = True

    elif enabled:
        paths = ', '.join(
            [name for name, status in created.items() if not status]
        )
        message = '. But'.join([hook_success, create_fail % paths])
        success = False

    else:
        paths = ', '.join(
            [name for name, status in created.items() if not status]
        )
        message = '. And'.join([hook_failure, create_fail % paths])
        success = False

    response = {
        'message': message,
        'success': success
    }

    return response


def github_path_exists(repo, path):
    """ Return True if the given repository has the given path. """

    #fixme: make this an authenticated request.

    url = 'repos/%s/contents/%s' % (repo, path)
    url = 'https://api.github.com/' + url

    return requests.get(url).status_code == 200


def is_travis_user(gh_token):
    """ Return True if the user has an account on Travis CI. """

    token    = get_travis_access_token(gh_token)
    headers  = {
        'Authorization': 'token %s' % token,
        'Content-Type': 'application/json; charset=UTF-8'
    }
    app.logger.info('Checking if current user is a travis user')
    response = requests.get(
        'https://api.travis-ci.org/users/', headers=headers
    )

    if response.status_code == 200:
        synced_at = response.json().get('synced_at')
    else:
        synced_at = None

    return synced_at is not None


def is_valid_repo(repo):
    """ Return True if such a repo exists on GitHub. """

    response = requests.get('https://github.com/%s' % repo)
    return response.status_code == 200


def render_readme():
    """ Render the README file as a template file. """

    with open(join(HERE, 'README.md')) as f:
        with open(join(HERE, 'templates', 'readme.html'), 'w') as g:
            readme = markdown(f.read())
            g.write(readme)


def sync_and_get_repo_id(repo, gh_token):
    """ Sync repositories of the user from GitHub and try to get repo id. """

    synced = sync_travis_with_github(gh_token)

    if synced:
        repo_id = get_repo_id(repo)

    else:
        repo_id = None

    return repo_id


def sync_travis_with_github(gh_token):
    """ Sync the repositories of the user from GitHub. """

    token    = get_travis_access_token(gh_token)
    headers  = {
        'Authorization': 'token %s' % token,
        'Content-Type': 'application/json; charset=UTF-8'
    }
    response = requests.post(
        'http://api.travis-ci.org/users/sync', headers=headers
    )

    if response.status_code == 200 and response.json()['result']:
        # fixme: this is ugly. should we make this async?
        synced = wait_until_sync_finishes(headers)
    else:
        synced = False

    return synced


def wait_until_sync_finishes(headers):
    """ Wait until a sync finishes. """

    count = 0

    while count < 50:
        count += 1
        response = requests.get(
            'http://api.travis-ci.org/users/', headers=headers
        )

        if response.status_code != 200:
            status = False
            break
        elif response.json()['is_syncing']:
            status = False
        else:
            status = True
            break

    return status

#### Standalone ###############################################################

if __name__ == '__main__':
    db.create_all()
    render_readme()
    app.run(host='0.0.0.0')

#### EOF ######################################################################
