""" A web app to automate build and deployment of static sites on GitHub. """

# Standard library.
import json

# 3rd party library.
from flask import flash, Flask, redirect, render_template, request, url_for
from flask_login import (
    LoginManager, login_user, login_required, logout_user, UserMixin,
    current_user
)
from flask.ext.sqlalchemy import SQLAlchemy
from rauth.service import OAuth2Service
import requests

AUTHORIZE_URL = 'https://github.com/login/oauth/authorize'

# Flask setup
app = Flask(__name__)
app.config.from_pyfile('settings.py')
db = SQLAlchemy(app)

# Login related
login_manager = LoginManager()
login_manager.init_app(app)

# rauth OAuth 2.0 service wrapper
github = OAuth2Service(
    client_id=app.config['CLIENT_ID'],
    client_secret=app.config['CLIENT_SECRET'],
    name='github',
    authorize_url=AUTHORIZE_URL,
    access_token_url='https://github.com/login/oauth/access_token',
    base_url='https://api.github.com/'
)


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
    return render_template('login.html', user=current_user)


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

    flash('Logged in as ' + user.get('name', user['login']))
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


@app.route('/manage')
@login_required
def manage():
    repo    = request.args.get('repo', None)
    repo_id = get_repo_id(repo)

    if repo is None:
        message = 'Need a valid repository name'

    elif not is_travis_user(current_user.access_token):
        message = ('You do not have a travis account. '
                   'Please <a href="https://travis-ci.org/profile" '
                   'target="_blank">signup</a>')

    elif repo_id is None:
        if is_valid_repo(repo):
            # fixme: can we try to sync?
            message = ('Repo could not be found.  '
                       'If this is "your" repo, please run a sync')
        else:
            message = 'No such repository exists!'

    else:
        enabled = enable_ci_for_repo(repo_id, current_user.access_token)
        if enabled:
            message = 'Successfully enabled publishing for %s' % repo
        else:
            message = (
                'Failed to enable publishing for %s.  '
                'Do you have the required permissions?' % repo
            )

    #access_token = current_user.access_token
    return message


#### Helper functions #########################################################

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
        response = requests.put(url, data=payload,  headers=headers)
        status = response.status_code == 200

    return status


def get_repo_id(repo):
    """ Get the id for a repo. """

    if repo is not None:
        url      = 'https://api.travis-ci.org/repos/%s' % repo
        response = requests.get(url).json()

    else:
        response = {}

    return response.get('id')


def get_travis_access_token(gh_token):

    url = 'https://api.travis-ci.org/auth/github'
    data = {'github_token': gh_token}

    return requests.post(url, data=data).json().get('access_token')


def is_travis_user(gh_token):
    """ Return True if the user has an account on Travis CI. """

    token    = get_travis_access_token(gh_token)
    headers  = {
        'Authorization': 'token %s' % token,
        'Content-Type': 'application/json; charset=UTF-8'
    }
    response = requests.get('http://api.travis-ci.org/users/', headers=headers)

    if response.status_code == 200:
        synced_at = response.json().get('synced_at')
    else:
        synced_at = None

    return synced_at is not None


def is_valid_repo(repo):
    """ Return True if such a repo exists on GitHub. """

    response = requests.get('https://github.com/%s' % repo)
    return response.status_code == 200


#### Standalone ###############################################################

if __name__ == '__main__':
    db.create_all()
    app.run(host='0.0.0.0')

#### EOF ######################################################################
