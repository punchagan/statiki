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


class TravisUtils(object):
    """ A collection of helper functions for consuming the Travis CI API. """

    @staticmethod
    def enable_hook(repo_id, token):
        """ Enable the travis hook for the repository with the given id. """

        payload  = json.dumps(dict(hook=dict(active=True, id=repo_id)))
        headers  = TravisUtils.get_header(token)
        url      = 'https://api.travis-ci.org/hooks/%s' % repo_id
        response = requests.put(url, data=payload,  headers=headers)

        return response.status_code == 200

    @staticmethod
    def get_access_token(github_token):

        url = 'https://api.travis-ci.org/auth/github'
        data = {'github_token': github_token}

        return requests.post(url, data=data).json().get('access_token')

    @staticmethod
    def get_encrypted_text(repo_name, data):
        """ Return encrypted text for the data. """

        public_key = TravisUtils.get_public_key(repo_name)
        key = rsa.PublicKey.load_pkcs1_openssl_pem(public_key)
        secure = base64.encodestring(rsa.encrypt(data, key))
        secure, _ = re.subn('\s+', '', secure)

        return secure

    @staticmethod
    def get_header(token):
        """ Return a header with authorization info, given the token. """

        return {
            'Authorization': 'token %s' % token,
            'Content-Type': 'application/json; charset=UTF-8'
        }

    @staticmethod
    def get_public_key(repo):
        """ Get a public key for the repository from travis. """

        url = 'https://api.travis-ci.org/repos/%s' % repo
        response = requests.get(url)

        return response.json()['public_key'].replace('RSA PUBLIC', 'PUBLIC')

    @staticmethod
    def get_repo_id(full_name, token):
        """ Get the id for a repository from travis. """

        if TravisUtils.hook_exists(full_name, token):
            url      = 'https://api.travis-ci.org/repos/%s' % full_name
            response = requests.get(url).json()
            repo_id = response.get('id')

        else:
            repo_id = None

        return repo_id

    @staticmethod
    def get_script_contents(full_name):
        """ Get the contents of the script to be run on travis. """

        template = join(
            dirname(__file__), 'utils', 'travis_script_template.sh'
        )
        with open(template) as f:
            contents = f.read()

        return contents % {'REPO': full_name}

    @staticmethod
    def get_status():
        """ Return the server status of GitHub. """

        response = requests.get('http://status.travis-ci.com')
        pattern  = '(<div.*?class="page-status.*".*>((.|\s)*?)</div>)'

        return re.findall(pattern, response.text)[0][1].strip()

    @staticmethod
    def get_yaml_contents(full_name, github_token):
        """ Get the contents to be dumped into .travis.yml. """

        data   = 'GITHUB_TOKEN=%s GIT_NAME=%s GIT_EMAIL=%s' % (
            github_token.encode(), 'Travis CI', 'testing@travis-ci.org'
        )
        secure = TravisUtils.get_encrypted_text(full_name, data)

        config = {
            'env': {'global': {'secure': secure}},
            'install': [
                'wget https://github.com/getnikola/wheelhouse/archive/v2.7.zip',
                'unzip v2.7.zip',
                'pip install --use-wheel --no-index --find-links=wheelhouse-2.7 lxml Pillow',
                'rm -rf wheelhouse-2.7 v2.7.zip',
                'pip install nikola webassets',
            ],
            'branches': {'only': ['master']},
            'language': 'python',
            'python': ['2.7'],
            'script': 'bash %(SCRIPT)s',
        }

        return yaml.dump(config)

    @staticmethod
    def hook_exists(full_name, token):
        """ Return True if a hook for the repository is listed on travis. """

        headers  = {
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

    @staticmethod
    def is_travis_user(github_token):
        """ Check if a user is a Travis user.

        Return the travis token if so, else None.

        """

        travis_token = TravisUtils.get_access_token(github_token)
        headers      = {
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

    @staticmethod
    def start_sync(token):
        """ Start syncing repositories for the user with the given token. """

        headers  = TravisUtils.get_header(token)
        response = requests.post(
            'http://api.travis-ci.org/users/sync', headers=headers
        )

        return (
            response.json()['result'] if response.status_code == 200
            else False
        )

    @staticmethod
    def sync_with_github(token):
        """ Sync the repositories of the user on Travis from GitHub. """

        if TravisUtils.start_sync(token):
            synced = TravisUtils.wait_to_sync(token)
        else:
            synced = False

        return synced

    @staticmethod
    def wait_to_sync(token):
        """ Wait until a sync finishes. """

        import time

        headers = TravisUtils.get_header(token)

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
