""" A web app to automate build and deployment of static sites on GitHub. """

# 3rd party library.
from flask import flash, Flask, redirect, render_template, request, url_for
from flask.ext.sqlalchemy import SQLAlchemy
from rauth.service import OAuth2Service

AUTHORIZE_URL = 'https://github.com/login/oauth/authorize'

# Flask setup
app = Flask(__name__)
app.config.from_pyfile('settings.py')
db = SQLAlchemy(app)

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

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    gh_id = db.Column(db.String(120))
    access_token = db.Column(db.String(40))

    def __init__(self, username, gh_id):
        self.username = username
        self.gh_id = gh_id

    def __repr__(self):
        return '<User %r>' % self.username

    @staticmethod
    def get_or_create(username, gh_id):
        user = User.query.filter_by(username=username).first()
        if user is None:
            user = User(username, gh_id)
            db.session.add(user)
            db.session.commit()
        return user


#### views ####################################################################

@app.route('/')
def index():
    return render_template('login.html')


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
    user_obj.access_token = session.access_token

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

#### Standalone ###############################################################

if __name__ == '__main__':
    db.create_all()
    app.run(host='0.0.0.0')

#### EOF ######################################################################
