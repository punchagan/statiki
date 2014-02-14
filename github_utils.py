# -*- coding: utf-8 -*-

# Copyright © 2014 Puneeth Chaganti and others.
# See the LICENSE file for license rights and limitations (MIT).

""" A collection of helper functions for consuming the GitHub API. """

# Standard library
import base64
import json
import re

# 3rd party library
import requests


class GitHubUtils(object):
    """ A collection of helper functions for consuming the GitHUb API. """

    @staticmethod
    def commit(path, content, repo, token, extra_payload=None):
        """ Commit the given content to the given path in a repository. """

        branch = 'deploy' if GitHubUtils.is_user_pages(repo) else 'master'
        headers = GitHubUtils.get_header(token)
        payload = {
            'path': path,
            'message': 'Adding %s (from statiki).' % path,
            'content': base64.standard_b64encode(content),
            'branch': branch
        }

        if extra_payload is not None:
            payload.update(extra_payload)

        sha = GitHubUtils.exists(repo, path, token)
        if sha is not None:
            payload['sha'] = sha

        url = 'https://api.github.com/repos/%s/contents/%s' % (repo, path)

        response = requests.put(
            url, data=json.dumps(payload), headers=headers
        )

        return response.ok

    @staticmethod
    def create_new_repository(full_name, token):
        """ Create a new repository given the name and a token.

        NOTE the token must have 'repo' scope, not just 'public_repo'.

        """

        user, user_type, name = GitHubUtils.get_user_and_repo(
            full_name, token
        )

        url = 'https://api.github.com/user/repos'
        headers = GitHubUtils.get_header(token)
        homepage = (
            name if GitHubUtils.is_user_pages(full_name)
            else 'http://%s.github.io/%s' % (user, name)
        )
        payload = {
            'name': name,
            'description': 'Website using Nikola, created from statiki',
            'homepage': homepage,
            'private': False,
            'has_issues': False,
            'has_wiki': False,
            'has_downloads': False,
        }

        response = requests.post(
            url, data=json.dumps(payload), headers=headers
        )

        return response.status_code == 201

    @staticmethod
    def exists(full_name, path, token):
        """ Return the sha of a path in a repo, if it exists; else None. """

        headers = GitHubUtils.get_header(token)

        url = 'repos/%s/contents/%s' % (full_name, path)
        url = 'https://api.github.com/' + url

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            sha = json.loads(response.text)['sha']

        else:
            sha = None

        return sha

    @staticmethod
    def get_header(token):
        """ Return a header with authorization info, given the token. """

        return {
            'Authorization': 'token %s' % token,
            'Content-Type': 'application/json'
        }

    @staticmethod
    def get_status():
        """ Return the server status of GitHub. """

        response = requests.get('https://status.github.com')
        pattern  = '(<div.*?id="message".*>(.|\s)*?</div>)'

        return re.findall(pattern, response.text)[0][0].strip()

    @staticmethod
    def get_user_and_repo(full_name, token):
        """ Return the username, user_type, repo_name, given a repository.

        user_type is one of User or Organization.

        """

        user, name = full_name.split('/')
        url = 'https://api.github.com/users/%s' % user
        headers = GitHubUtils.get_header(token)

        response = requests.get(url, headers=headers)

        user_type = response.json()['type']

        return user, user_type, name

    @staticmethod
    def is_valid_repository(full_name):
        """ Return True if such a repo exists on GitHub. """

        response = requests.get('https://github.com/%s' % full_name)
        return response.status_code == 200

    @staticmethod
    def is_user_pages(full_name):
        """ Return True if the repository is a user pages repository. """

        username, repo_name = full_name.split('/', 1)

        return (
            repo_name.startswith(username)
            and repo_name.endswith(('github.io', 'github.com'))
        )
