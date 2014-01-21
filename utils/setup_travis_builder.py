""" A command line tool to automate everything for an existing repo.

This script adds and/or tweaks a .travis.yml file and an additional script
to deploy using travis-ci to gh-pages branch on GitHub.

"""

# Standard library.
import json
import os
from os.path import dirname, exists, join

# 3rd party library.
import requests


def add_nojekyll(path):
    """ Add a .nojekyll file. """

    nojekyll = join(path, 'files', '.nojekyll')

    if not exists(nojekyll):

        if not exists(dirname(nojekyll)):
            os.makedirs(dirname(nojekyll))

        with open(nojekyll, 'w') as f:
            pass


def get_gh_auth_token():
    """ Get a token from GitHub to use for pushing from Travis. """

    from getpass import getpass

    username = raw_input('GitHub username: ')
    password = getpass('GitHub password: ')

    url = 'https://api.github.com/authorizations'
    data = {
        'scopes': ['public_repo'],
        'note': 'TravisCI deployment'
    }
    response = requests.post(
        url, data=json.dumps(data), auth=(username, password)
    )

    return response.json()['token']


def create_travis_config(path):
    """ Add .travis.yml. """

    import yaml

    travis_yml = join(path, '.travis.yml')

    if exists(travis_yml):
        print('%s already exists. Nothing to do.' % travis_yml)
        return

    # FIXME: enable hook here!
    # '/hooks' doesn't work as expected?

    data = 'GH_TOKEN=%s GIT_NAME=%s GIT_EMAIL=%s' % (
        get_gh_auth_token().encode(), 'Travis CI', 'testing@travis-ci.org'
    )
    secure = get_encrypted_text('punchagan/mumbaiultimate.in', data)
    nikola_repo = 'git+https://github.com/getnikola/nikola.git#egg=nikola'

    config = {
        'env': {'global': {'secure': secure}},
        'install': 'pip install -e %s' % nikola_repo,
        'language': 'python',
        'python': ['2.7'],
        'script': './build_and_deploy.sh'
    }

    with open(travis_yml, 'w') as f:
        yaml.dump(config, f)

    print('%s created. Add and commit to the git repo.' % travis_yml)


def get_travis_public_key(repo):
    """ Get a public key for the repository from travis. """

    url = 'https://api.travis-ci.org/repos/%s' % repo
    response = requests.get(url)

    return response.json()['public_key'].replace('RSA PUBLIC', 'PUBLIC')


def get_encrypted_text(repo_name, data):
    """ Return encrypted text for the data. """

    import rsa
    import re
    import base64

    public_key = get_travis_public_key(repo_name)
    key = rsa.PublicKey.load_pkcs1_openssl_pem(public_key)
    secure = base64.encodestring(rsa.encrypt(data, key))
    secure, _ = re.subn('\s+', '', secure)

    return secure


def create_script_file(path):
    """ Create the script file that will be run, to build and deploy. """


def main(args):

    if len(args) != 2:
        print 'Usage: %s /path/to/repo' % args[0]
        sys.exit()

    path = os.path.abspath(args[1])
    add_nojekyll(path)
    create_travis_config(path)
    create_script_file(path)


if __name__ == "__main__":
    import sys
    main(sys.argv)
