""" A command line tool to automate everything for an existing repo.

This script adds and/or tweaks a .travis.yml file and an additional script
to deploy using travis-ci to gh-pages branch on GitHub.

Usage:
    %s <repo-name> [<path-to-dir>]

Requires:
  - docopt
  - pyyaml
  - requests
  - rsa

"""

# Standard library.
import base64
import json
import os
from os.path import basename, dirname, exists, join
import re

# 3rd party library.
import requests
import rsa
import yaml

SCRIPT = './travis_build_n_deploy.sh'


def add_nojekyll(path):
    """ Add a .nojekyll file. """

    nojekyll = join(path, 'files', '.nojekyll')

    if not exists(nojekyll):

        if not exists(dirname(nojekyll)):
            os.makedirs(dirname(nojekyll))

        with open(nojekyll, 'w') as f:
            pass


def create_travis_config(path, repo):
    """ Add .travis.yml. """

    travis_yml = join(path, '.travis.yml')

    if exists(travis_yml):
        print('%s already exists. Nothing to do.' % travis_yml)
        return

    gh_token = get_gh_auth_token().encode()
    enable_ci_for_repo(repo, gh_token)
    data = 'GH_TOKEN=%s GIT_NAME=%s GIT_EMAIL=%s' % (
        gh_token, 'Travis CI', 'testing@travis-ci.org'
    )
    secure = get_encrypted_text(repo, data)

    config = {
        'env': {'global': {'secure': secure}},
        'install': ['wget https://github.com/getnikola/wheelhouse/archive/v2.7.zip', 'unzip v2.7.zip',
                    'pip install --use-wheel --no-index --find-links=wheelhouse-2.7 lxml Pillow',
                    'pip install nikola webassets'],
        'branches': {'only': ['master']},
        'language': 'python',
        'python': ['2.7'],
        'script': SCRIPT,
        'virtualenv': {'system_site_packages': True},
    }

    with open(travis_yml, 'w') as f:
        yaml.dump(config, f)

    print('%s created. Add and commit to the git repo.' % travis_yml)


def create_script_file(path, repo):
    """ Create the script file that will be run, to build and deploy. """

    script = join(path, SCRIPT)

    if exists(script):
        print('%s already exists. Nothing to do' % script)
        return

    template = join(dirname(__file__), 'travis_script_template.sh')
    with open(template) as f:
        contents = f.read()

    with open(script, 'w') as f:
        f.write(contents % {'REPO': repo})

    os.chmod(script, 0755)

    print('%s created. Add and commit to the git repo.' % script)


def enable_ci_for_repo(repo, gh_token):
    """ Enable the travis hook for the given repo. """

    repo_id = get_repo_id(repo)
    access_token = get_travis_access_token(gh_token)
    payload = json.dumps(dict(hook=dict(active=True, id=repo_id)))
    headers = {
        'Authorization': 'token %s' % access_token,
        'Content-Type': 'application/json; charset=UTF-8'
    }
    url = 'https://api.travis-ci.org/hooks/%s' % repo_id
    requests.put(url, data=payload,  headers=headers)
    print('Enabled GitHub/Travis hook for %s' % repo)


def get_encrypted_text(repo_name, data):
    """ Return encrypted text for the data. """

    public_key = get_travis_public_key(repo_name)
    key = rsa.PublicKey.load_pkcs1_openssl_pem(public_key)
    secure = base64.encodestring(rsa.encrypt(data, key))
    secure, _ = re.subn('\s+', '', secure)

    return secure


def get_gh_auth_token(note='TravisCI deployment'):
    """ Get a token from GitHub to use for pushing from Travis. """

    from getpass import getpass

    username = raw_input('GitHub username: ')
    password = getpass('GitHub password: ')

    url = 'https://api.github.com/authorizations'
    data = {
        'scopes': ['repo'],
        'note': note
    }
    response = requests.post(
        url, data=json.dumps(data), auth=(username, password)
    )

    return response.json()['token']


def get_repo_id(repo):
    """ Get the id for a repo. """

    url = 'https://api.travis-ci.org/repos/%s' % repo

    return requests.get(url).json()['id']


def get_travis_access_token(gh_token):

    url = 'https://api.travis-ci.org/auth/github'
    data = {'github_token': gh_token}

    return requests.post(url, data=data).json()['access_token']


def get_travis_public_key(repo):
    """ Get a public key for the repository from travis. """

    url = 'https://api.travis-ci.org/repos/%s' % repo
    response = requests.get(url)

    return response.json()['public_key'].replace('RSA PUBLIC', 'PUBLIC')


def main():
    """ Main entry point. """

    from docopt import docopt
    args = docopt(__doc__ % basename(__file__))
    repo = args['<repo-name>']
    path = os.path.abspath(args['<path-to-dir>'] or '.')

    add_nojekyll(path)
    create_travis_config(path, repo)
    create_script_file(path, repo)


if __name__ == "__main__":
    main()
