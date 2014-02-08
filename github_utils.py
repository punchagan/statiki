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

        if not GitHubUtils.exists(repo, path, token):

            url = 'repos/%s/contents/%s' % (repo, path)
            url = 'https://api.github.com/' + url

            headers = GitHubUtils.get_header(token)

            payload = {
                'path': path,
                'message': 'Adding %s (from statiki).' % path,
                'content': base64.standard_b64encode(content),
            }

            if extra_payload is not None:
                payload.update(extra_payload)

            response = requests.put(
                url, data=json.dumps(payload), headers=headers
            )

            committed = response.status_code == 201

        else:
            committed = False

        return committed

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
        payload = {
            'name': name,
            'description': 'Website using Nikola, created from statiki',
            'homepage': 'http://%s.github.io/%s' % (user, name),
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
        """ Return True if the given repository has the given path. """

        headers = GitHubUtils.get_header(token)

        url = 'repos/%s/contents/%s' % (full_name, path)
        url = 'https://api.github.com/' + url

        return requests.get(url, headers=headers).status_code == 200

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

