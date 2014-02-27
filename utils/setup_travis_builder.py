# -*- coding: utf-8 -*-

# Copyright © 2014 Puneeth Chaganti and others.
# See the LICENSE file for license rights and limitations (MIT).

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
  - github_utils (from statiki)
  - travis_utils (from statiki)

  - travis_script_template.sh (present along with this file)

"""

# Standard library.
import json
import os
from os.path import basename, dirname, exists, join
import shutil

# 3rd party library.
import requests

# Local library
from travis_utils import TravisUtils

SCRIPT = './travis_fabfile.py'
GIT_NAME = 'Statiki'
GIT_EMAIL = 'noreply@statiki.herokuapp.com'
# fixme: currently writes to some dumb path. Use .gitconfig?
GH_TOKEN_FILE = join(dirname(__file__), '.gh_token')


def add_nojekyll(path):
    """ Add a .nojekyll file. """

    nojekyll = join(path, 'files', '.nojekyll')

    if not exists(nojekyll):

        if not exists(dirname(nojekyll)):
            os.makedirs(dirname(nojekyll))

        with open(nojekyll, 'w') as f:
            pass


def create_travis_config(path, repo, gh_token):
    """ Add .travis.yml. """

    travis_yml = join(path, '.travis.yml')

    if exists(travis_yml):
        print('%s already exists. Nothing to do.' % travis_yml)
        return

    info = dict(GIT_NAME=GIT_NAME, GIT_EMAIL=GIT_EMAIL, GH_TOKEN=gh_token)
    content = TravisUtils.get_yaml_contents(repo, SCRIPT, info)

    with open(travis_yml, 'w') as f:
        f.write(content)

    print('%s created. Add and commit to the git repo.' % travis_yml)


def create_script_file(path):
    """ Create the script file that will be run, to build and deploy. """

    script = join(path, SCRIPT)

    if exists(script):
        print('%s already exists. Nothing to do' % script)
        return

    template = join(dirname(__file__), 'travis_script_template.sh')
    shutil.copy(template, script)

    print('%s copied. Add and commit to the git repo.' % script)


def enable_ci_for_repo(repo, gh_token):
    """ Enable the travis hook for the given repo. """

    access_token = TravisUtils.get_access_token(gh_token)
    repo_id      = TravisUtils.get_repo_id(repo, access_token)
    enabled = TravisUtils.enable_hook(repo_id, access_token)
    if enabled:
        print('Enabled GitHub/Travis hook for %s' % repo)

    else:
        print('Failed to enable GitHub/Travis hook for %s' % repo)


def get_gh_auth_token(note='Statiki commandline script'):
    """ Get a token from GitHub to use for pushing from Travis. """

    token = read_gh_token()

    if token is None:

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

        token = response.json()['token'].encode()
        write_gh_token(token)

    return token


def read_gh_token():
    """ Read the token from the token file. """

    if not exists(GH_TOKEN_FILE):
        token = None

    else:
        with open(GH_TOKEN_FILE) as f:
            token = f.read().strip()

    return token


def write_gh_token(token):
    """ Write the token to the token file. """

    with open(GH_TOKEN_FILE, 'w') as f:
        f.write(token)

    return


def main():
    """ Main entry point. """

    from docopt import docopt
    args = docopt(__doc__ % basename(__file__))
    repo = args['<repo-name>']
    path = os.path.abspath(args['<path-to-dir>'] or '.')

    add_nojekyll(path)
    gh_token = get_gh_auth_token()
    create_travis_config(path, repo, gh_token)
    create_script_file(path)
    enable_ci_for_repo(repo, gh_token)


if __name__ == "__main__":
    main()
