# -*- coding: utf-8 -*-

# Copyright © 2014 Puneeth Chaganti and others.
# See the LICENSE file for license rights and limitations (MIT).

""" A collection of helper functions for consuming the Travis CI API. """

# Standard library
import base64
import json
from os.path import dirname, join
import re

# 3rd party library
import requests
import rsa
import yaml


def enable_hook(repo_id, token):
    """ Enable the travis hook for the repository with the given id. """

    payload = json.dumps(dict(hook=dict(active=True, id=repo_id)))
    headers = get_header(token)
    url = 'https://api.travis-ci.org/hooks/%s' % repo_id
    response = requests.put(url, data=payload, headers=headers)

    return response.status_code == 200


def get_access_token(github_token):
    url = 'https://api.travis-ci.org/auth/github'
    data = {'github_token': github_token}

    return requests.post(url, data=data).json().get('access_token')


def get_encrypted_text(repo_name, data):
    """ Return encrypted text for the data. """

    public_key = get_public_key(repo_name)

    if len(public_key) > 0:
        key = rsa.PublicKey.load_pkcs1_openssl_pem(public_key)
        secure = base64.encodestring(rsa.encrypt(data, key))
        secure, _ = re.subn('\s+', '', secure)

    else:
        secure = 'Some encrypted data ...'

    return secure


def get_header(token):
    """ Return a header with authorization info, given the token. """

    return {
        'Authorization': 'token %s' % token,
        'Content-Type': 'application/json; charset=UTF-8'
    }


def get_public_key(repo):
    """ Get a public key for the repository from travis. """

    url = 'https://api.travis-ci.org/repos/%s' % repo
    response = requests.get(url)

    public_key = response.json().get('public_key', '')

    return public_key.replace('RSA PUBLIC', 'PUBLIC')


def get_repo_id(full_name, token):
    """ Get the id for a repository from travis. """

    if hook_exists(full_name, token):
        url = 'https://api.travis-ci.org/repos/%s' % full_name
        response = requests.get(url).json()
        repo_id = response.get('id')

    else:
        repo_id = None

    return repo_id


def get_script_contents(script_name, config=None):
    """ Get the contents of the script to be run on travis. """

    with open(join(dirname(__file__), 'utils', script_name)) as f:
        contents = f.read()

    if config:
        from pprint import pformat

        contents = contents.replace(
            'DATA = {}', 'DATA = %s' % pformat(config)
        )

    return contents


def get_status():
    """ Return the server status of GitHub. """

    response = requests.get('http://status.travis-ci.com')
    pattern = '(<div.*?class="page-status.*".*>((.|\s)*?)</div>)'

    return re.findall(pattern, response.text)[0][1].strip()


def get_yaml_contents(full_name, script_name, git_info, user_pages=False):
    """ Get the contents to be dumped into .travis.yml. """

    branch = 'deploy' if user_pages else 'master'

    data = (
        'GH_TOKEN={GH_TOKEN} '
        'GIT_NAME={GIT_NAME} '
        'GIT_EMAIL={GIT_EMAIL}'
    ).format(**git_info)
    secure = get_encrypted_text(full_name, data)

    config = {
        'env': {'global': {'secure': secure}},
        'install': [
            'wget https://github.com/getnikola/wheelhouse/archive/v2.7.zip',
            'unzip v2.7.zip',
            'pip install --use-wheel --no-index --find-links=wheelhouse-2.7 lxml Pillow',
            'rm -rf wheelhouse-2.7 v2.7.zip',
            'pip install fabric "nikola>=6.4.0" webassets',
        ],
        'branches': {'only': [branch]},
        'language': 'python',
        'python': ['2.7'],
        'script': 'fab -f %s main' % script_name,
    }

    return yaml.dump(config)


def hook_exists(full_name, token):
    """ Return True if a hook for the repository is listed on travis. """

    headers = {
        'Authorization': 'token %s' % token,
    }
    response = requests.get(
        'http://api.travis-ci.org/hooks', headers=headers
    )

    owner, name = full_name.split('/')
    if response.status_code == 200:
        repositories = [
            repo for repo in response.json()
            if repo['name'] == name and repo['owner_name'] == owner
        ]
        hook_exists = len(repositories) > 0

    else:
        hook_exists = False

    return hook_exists


def is_travis_user(github_token):
    """ Check if a user is a Travis user.

    Return the travis token if so, else None.

    """

    travis_token = get_access_token(github_token)
    headers = {
        'Authorization': 'token %s' % travis_token,
        'Content-Type': 'application/json; charset=UTF-8'
    }

    response = requests.get(
        'https://api.travis-ci.org/users/', headers=headers
    )

    if response.status_code == 200:
        synced_at = response.json().get('synced_at')
    else:
        synced_at = None

    return travis_token if synced_at is not None else None


def start_sync(token):
    """ Start syncing repositories for the user with the given token. """

    headers = get_header(token)
    response = requests.post(
        'http://api.travis-ci.org/users/sync', headers=headers
    )

    return (
        response.json()['result'] if response.status_code == 200
        else False
    )


def sync_with_github(token):
    """ Sync the repositories of the user on Travis from GitHub. """

    if start_sync(token):
        synced = wait_to_sync(token)
    else:
        synced = False

    return synced


def wait_to_sync(token):
    """ Wait until a sync finishes. """

    import time

    headers = get_header(token)

    for count in range(6):

        response = requests.get(
            'http://api.travis-ci.org/users/', headers=headers
        )

        if response.status_code == 200:
            if response.json()['is_syncing']:
                finished = False
                time.sleep(2 ** count)
            else:
                finished = True
                break
        else:
            finished = False
            break

    return finished
