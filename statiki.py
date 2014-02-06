""" A web app to automate build and deployment of static sites on GitHub. """

# Standard library.
from functools import wraps
from os.path import abspath, dirname, exists, join

# 3rd party library.
from flask import (
    flash, Flask, jsonify, redirect, render_template, request, url_for
)
from flask_login import (
    current_user, LoginManager, login_user, login_required, logout_user,
    UserMixin
)
from flask_sqlalchemy import SQLAlchemy
from rauth.service import OAuth2Service

# Local library.
import messages
from github_utils import GitHubUtils
from travis_utils import TravisUtils

AUTHORIZE_URL = 'https://github.com/login/oauth/authorize'
SCRIPT = 'travis_build_n_deploy.sh'
HERE = dirname(abspath(__file__))
SITE = 'Statiki'
DESCRIPTION = 'An easy-to-use service for deploying simple web-sites'
GIT_NAME = 'Travis CI'
GIT_EMAIL = 'bogus@travis-ci.org'


# Flask setup
app = Flask(__name__)
settings_path = join(HERE, 'settings.py')
app.config.from_pyfile(settings_path)
db = SQLAlchemy(app)

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
        travis_token = TravisUtils.is_travis_user(current_user.github_token)
        if travis_token is None:
            return jsonify(dict(message=messages.NO_TRAVIS_ACCOUNT))
        else:
            current_user.set_travis_token(travis_token)
        return func(*args, **kwargs)
    return decorated_view


#### models ###################################################################

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    gihub_id = db.Column(db.String(120))
    github_token = db.Column(db.String(40))
    travis_token = db.Column(db.String(40))

    def __init__(self, username, gh_id):
        self.username = username
        self.gihub_id = gh_id

    def __repr__(self):
        return '<User %r>' % self.username

    def set_github_token(self, github_token):
        self.github_token = github_token
        db.session.commit()

    def set_travis_token(self, travis_token):
        self.travis_token = travis_token
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
        flash(messages.AUTH_DECLINED)
        return redirect(url_for('index'))

    # make a request for the access token credentials using code
    redirect_uri = url_for('authorized', _external=True)
    data = dict(code=request.args['code'], redirect_uri=redirect_uri)

    session = github.get_auth_session(data=data)

    # the "me" response
    user = session.get('user').json()

    user_obj = User.get_or_create(user['login'], user['id'])
    user_obj.set_github_token(session.access_token)
    login_user(user_obj)

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
    logout_user()
    return redirect(url_for('index'))


@app.route('/manage', methods=['POST'])
@login_required
@travis_login_required
def manage():

    repo_name = request.form.get('repo_name', None)
    full_name = '%s/%s' % (current_user.username, repo_name)
    github_token = current_user.github_token
    travis_token = current_user.travis_token

    if not repo_name:
        message = messages.EMPTY_REPO_NAME
        return jsonify(dict(message=message))

    # If repo does not exist, create it.
    if not GitHubUtils.is_valid_repository(full_name):
        GitHubUtils.create_new_repository(full_name, github_token)

    # If repo not listed in travis, sync
    repo_id = TravisUtils.get_repo_id(full_name, travis_token)
    if repo_id is None:
        TravisUtils.sync_with_github(travis_token)
        repo_id = TravisUtils.get_repo_id(full_name, travis_token)

    if repo_id is None:
        message = messages.NO_SUCH_REPO_FOUND
        return jsonify(dict(message=message))

    enabled = TravisUtils.enable_hook(repo_id, travis_token)
    created = create_travis_files(full_name, github_token)

    response = get_display_response(enabled, created)
    response['message'] %= dict(
        USER=current_user.username,
        REPO=repo_name,
    )
    return jsonify(response)


@app.route('/status')
def show_status():

    context = {
        'user': current_user,
        'SITE': SITE,
        'DESCRIPTION': DESCRIPTION,
        'GITHUB_STATUS': GitHubUtils.get_status(),
        'TRAVIS_STATUS': TravisUtils.get_status(),
    }

    return render_template('status.html', **context)


#### Helper functions #########################################################

def create_travis_files(full_name, github_token):
    """ Create the files required for Travis CI hooks to work. """

    created       = {}
    git_user_info = {
        'GIT_NAME': GIT_NAME,
        'GIT_EMAIL': GIT_EMAIL,
        'GH_TOKEN': github_token
    }
    travis_files  = [
        {
            'name': SCRIPT,
            'content': TravisUtils.get_script_contents(full_name),
            'message': 'Adding build and deploy script. \n\n[skip ci]',
        },
        {
            'name': '.travis.yml',
            'content': TravisUtils.get_yaml_contents(
                full_name, git_user_info
            ) % dict(SCRIPT=SCRIPT),
            'message': 'Adding .travis.yml',
        },
    ]

    for file_ in travis_files:
        name          = file_['name']
        content       = file_['content']
        extra_payload = {
            'author': {
                'name': GIT_NAME,
                'email': GIT_EMAIL,
            },
            'committer': {
                'name': GIT_NAME,
                'email': GIT_EMAIL,
            },
            'message': file_['message']
        }

        created[name] = GitHubUtils.commit(
            name, content, full_name, github_token, extra_payload
        )

    return created


def get_display_response(enabled, created):
    """ Return the response for the user, based on enabled and created. """

    if enabled and all(created.values()):
        success = True
        message = messages.DONE

    elif enabled:
        message = messages.ONLY_HOOKS_ENABLED
        success = False

    else:
        message = messages.TOTAL_FAILURE
        success = False

    response = {
        'message': message,
        'success': success
    }

    return response


#### Standalone ###############################################################

if __name__ == '__main__':
    db.create_all()
    app.run(host='0.0.0.0')

#### EOF ######################################################################
