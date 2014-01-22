""" A command line tool to automate everything for an existing repo.

This script adds and/or tweaks a .travis.yml file and an additional script
to deploy using travis-ci to gh-pages branch on GitHub.

"""

# Standard library.
import json
import os
from os.path import basename, dirname, exists, join

# 3rd party library.
import requests

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
    secure = get_encrypted_text(repo, data)
    nikola_repo = 'git+https://github.com/getnikola/nikola.git#egg=nikola'

    config = {
        'env': {'global': {'secure': secure}},
        'install': 'pip install -e %s' % nikola_repo,
        'language': 'python',
        'python': ['2.7'],
        'script': SCRIPT
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


def get_arg_parser():
    """ Create an argument parser using docopt. """

    from docopt import docopt

    filename = basename(__file__)
    usage = """Usage:
    %s <repo-name> <path-to-dir>
    """ % filename

    return docopt(usage)


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


def get_travis_public_key(repo):
    """ Get a public key for the repository from travis. """

    url = 'https://api.travis-ci.org/repos/%s' % repo
    response = requests.get(url)

    return response.json()['public_key'].replace('RSA PUBLIC', 'PUBLIC')


def main():
    """ Main entry point. """

    args = get_arg_parser()
    repo = args['<repo-name>']
    path = os.path.abspath(args['<path-to-dir>'])

    add_nojekyll(path)
    create_travis_config(path, repo)
    create_script_file(path, repo)


if __name__ == "__main__":
    main()
