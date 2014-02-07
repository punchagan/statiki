# -*- coding: utf-8 -*-

# Copyright © 2014 Puneeth Chaganti and others.
# See the LICENSE file for license rights and limitations (MIT).

import json
import os
from mock import Mock, patch
import unittest

from github_utils import GitHubUtils


def get_gh_token(bogus):
    """ Returns the GH token to use. """
    # fixme: Change this to check if we are rate limited, an use BOGUS if so.

    token = os.environ.get('GH_TOKEN', bogus)

    return token

BOGUS = 'this-is-a-bogus-token'
THIS_REPO = 'punchagan/statiki'
GH_TOKEN = get_gh_token(BOGUS)


@unittest.skipIf(GH_TOKEN == BOGUS, 'Need a real GitHub token...')
class TestGitHubUtils(unittest.TestCase):

    def test_should_return_true_if_exists(self):
        self.assertTrue(
            GitHubUtils.exists(THIS_REPO, 'README.md', GH_TOKEN)
        )

    def test_should_return_false_if_non_existent(self):
        self.assertFalse(GitHubUtils.exists(THIS_REPO, 'README.xx', GH_TOKEN))

    def test_should_return_punchagan(self):
        self.assertEqual(
            GitHubUtils.get_user_and_repo(THIS_REPO, GH_TOKEN),
            ('punchagan', 'User', 'statiki')
        )

    def test_should_return_github(self):
        self.assertEqual(
            GitHubUtils.get_user_and_repo('github/gitignore', GH_TOKEN),
            ('github', 'Organization', 'gitignore')
        )

    def test_should_confirm_repository_exists(self):
        self.assertTrue(GitHubUtils.is_valid_repository(THIS_REPO))

    def test_should_detect_invalid_repository(self):
        self.assertFalse(GitHubUtils.is_valid_repository(THIS_REPO+'abc'))

    def test_should_commit_new_file(self):
        # Given
        full_name = 'punchagan/experiri'
        content = path = self._get_random_string()
        author = {
            'name': 'Tests on Travis',
            'email': 'travis-ci-tests@test.com',
        }
        info = {
            'author': author,
            'committer': author,
        }

        # When
        committed = GitHubUtils.commit(
            path, content, full_name, GH_TOKEN, extra_payload=info
        )

        # Then
        self.assertTrue(committed)
        self.assertTrue(GitHubUtils.exists(full_name, path, GH_TOKEN))

    def test_should_not_commit_to_existing_path(self):
        # Given
        full_name = 'punchagan/experiri'
        content = path = self._get_random_string()
        author = {
            'name': 'Tests on Travis',
            'email': 'travis-ci-tests@test.com',
        }
        info = {
            'author': author,
            'committer': author,
        }
        GitHubUtils.commit(path, content, full_name, GH_TOKEN, info)

        # When
        committed = GitHubUtils.commit(path, content*2, full_name, GH_TOKEN)

        # Then
        self.assertFalse(committed)

    def test_should_create_new_repository(self):
        # Given
        user = 'punchagan'
        repo = self._get_random_string(8)
        full_name = '%s/%s' % (user, repo)
        response = Mock(status_code=201)

        # When
        with patch('requests.post', Mock(return_value=response)) as post:
            created = GitHubUtils.create_new_repository(full_name, GH_TOKEN)

        # Then
        args, kwargs = post.call_args
        self.assertIn(GH_TOKEN, kwargs['headers']['Authorization'])
        self.assertEqual(repo, json.loads(kwargs['data'])['name'])
        self.assertTrue(created)

    def test_should_not_create_existing_repository(self):
        self.assertFalse(
            GitHubUtils.create_new_repository(THIS_REPO, GH_TOKEN)
        )

    def test_should_get_status(self):
        self.assertIn(
            'all systems operational', GitHubUtils.get_status().lower()
        )

    #### Private protocol #####################################################

    def _get_random_string(self, length=40):
        """ Return a random string of the specified length. """

        from random import choice
        import string

        return ''.join([choice(string.ascii_letters) for _ in range(length)])
