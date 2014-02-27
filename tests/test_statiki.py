# -*- coding: utf-8 -*-

# Copyright © 2014 Puneeth Chaganti and others.
# See the LICENSE file for license rights and limitations (MIT).

from contextlib import contextmanager
import json
import os
from os.path import abspath, exists, join
import shutil
import tempfile
import unittest

from mock import Mock, patch
from rauth.service import OAuth2Service
from requests import Response

import statiki
import messages


GH_TOKEN = 'this-is-a-bogus-token'
THIS_REPO = 'punchagan/statiki'


class TestStatiki(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.db_path = join(self.tempdir, 'test.db')
        statiki.app.config['SQLALCHEMY_DATABASE_URI'] = (
            'sqlite:///%s' % self.db_path
        )
        statiki.app.config['TESTING'] = True
        statiki.db.create_all()
        self.app = statiki.app.test_client()

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_should_create_travis_files(self):
        # Given
        expected = {
            statiki.SCRIPT: True,
            '.travis.yml': True
        }
        true = Mock(return_value=True)

        # When
        with patch('github_utils.GitHubUtils.commit', true) as commit:
            created = statiki.create_travis_files(THIS_REPO, GH_TOKEN)

        # Then
        args, _ = commit.call_args
        self.assertDictEqual(expected, created)
        self.assertIn(statiki.SCRIPT, args[1])

    def test_should_show_success(self):
        # Given
        enabled = True
        created = {
            statiki.SCRIPT: True,
            '.travis.yml': True
        }

        # When
        message = statiki.get_display_response(enabled, created)['message']

        # Then
        self.assertEqual(messages.DONE, message)

    def test_should_show_failure(self):
        # Given
        enabled = False
        created = {
            statiki.SCRIPT: False,
            '.travis.yml': True
        }

        # When
        message = statiki.get_display_response(enabled, created)['message']

        # Then
        self.assertEqual(messages.TOTAL_FAILURE, message)

    def test_should_show_partial_success(self):
        # Given
        enabled = True
        created = {
            statiki.SCRIPT: False,
            '.travis.yml': True
        }

        # When
        message = statiki.get_display_response(enabled, created)['message']

        # Then
        self.assertEqual(messages.ONLY_HOOKS_ENABLED, message)

    def test_should_show_index(self):
        # Given/When
        response = self.app.get('/')

        # Then
        self.assertEqual(200, response.status_code)
        self.assertIn(statiki.DESCRIPTION, response.data)

    def test_should_redirect_to_authorize_on_login(self):
        # Given/When
        response = self.app.get('/login')

        # Then
        self.assertEqual(302, response.status_code)
        self.assertIn(statiki.AUTHORIZE_URL, response.data)

    def test_should_return_to_login_if_not_authorized(self):
        # Given/When
        response = self.app.get('/authorized')
        next_response = self.app.get()

        # Then
        self.assertEqual(302, response.status_code)
        self.assertIn('<a href="/">/</a>', response.data)
        self.assertIn(messages.AUTH_DECLINED, next_response.data)

    def test_should_return_to_index_if_authorized(self):
        # Given/When
        with self.logged_in() as response:
            next_response = self.app.get()

        # Then
        self.assertEqual(302, response.status_code)
        self.assertIn('<a href="/">/</a>', response.data)
        self.assertIn('Logout', next_response.data)

    def test_should_redirect_to_index_on_logout(self):
        # Given/When
        with self.logged_in():
            response = self.app.get('/logout')
            next_response = self.app.get()

        # Then
        self.assertEqual(302, response.status_code)
        self.assertIn(statiki.DESCRIPTION, next_response.data)

    def test_should_show_travis_signup(self):
        # Given/When
        with self.logged_in(travis_user=False):
            response = self.app.post(
                '/create_repo', data=dict(repo_name='statiki')
            )

        # Then
        self.assertEqual(200, response.status_code)
        self.assertIn(json.dumps(messages.NO_TRAVIS_ACCOUNT), response.data)

    def test_should_create_repo(self):
        # Given
        target = 'github_utils.GitHubUtils.create_new_repository'
        content = [{'name': 'bazooka', 'content': 'bar', 'message': ''}]
        get_content = Mock(return_value=content)

        # When
        with self.logged_in('punchagan'):
            with patch(target, Mock()) as create:
                with patch('statiki.get_travis_files_content', get_content):
                    response = self.app.post(
                        '/create_repo', data={'repo_name': 'foo'}
                    )

        # Then
        args, _ = create.call_args
        self.assertEqual(args, ('punchagan/foo', GH_TOKEN))
        data = json.loads(response.data)
        self.assertTrue(data['created'])
        self.assertIn('bazooka', data['contents'])
        self.assertIn('bar', data['contents'])
        self.assertEqual(messages.CREATE_REPO_SUCCESS, data['message'])

    def test_should_inform_create_repo_failure(self):
        # Given
        target = 'github_utils.GitHubUtils.create_new_repository'
        create_repo = Mock(return_value=False)

        # When
        with self.logged_in('bazooka'):
            with patch(target, create_repo):
                response = self.app.post(
                    '/create_repo', data={'repo_name': ''}
                )

        # Then
        args, _ = create_repo.call_args
        self.assertEqual(args, ('bazooka/bazooka.github.io', GH_TOKEN))
        data = json.loads(response.data)
        self.assertFalse(data['created'])
        self.assertEqual(messages.CREATE_REPO_FAILURE, data['message'])

    def test_should_prompt_statiki_files_overwrite(self):
        # Given/When
        true = Mock(return_value=True)
        with self.logged_in('punchagan'):
            with patch('github_utils.GitHubUtils.exists', true):
                response = self.app.post(
                    '/create_repo', data={'repo_name': 'statiki'}
                )

        # Then
        data = json.loads(response.data)
        self.assertFalse(data['created'])
        self.assertTrue(data['exists'])
        self.assertTrue(data['overwrite'])
        self.assertEqual(messages.OVERWRITE_YAML, data['message'])

    def test_should_manage_repo_with_no_statiki_files(self):
        # Given/When
        false = Mock(return_value=False)
        with self.logged_in('punchagan'):
            with patch('github_utils.GitHubUtils.exists', false):
                response = self.app.post(
                    '/create_repo', data={'repo_name': 'statiki'}
                )

        # Then
        data = json.loads(response.data)
        self.assertFalse(data['created'])
        self.assertTrue(data['exists'])
        self.assertFalse(data['overwrite'])
        self.assertEqual(messages.REPO_EXISTS, data['message'])

    def test_should_manage_this_repo(self):
        # Given
        target = 'travis_utils.TravisUtils.get_repo_id'

        # When/Then
        with self.logged_in('punchagan'):
            with patch(target, Mock(return_value=1779263)):
                response = self.app.post(
                    '/manage', data={'full_name': 'punchagan/statiki'}
                )

        # Then
        self.assertEqual(200, response.status_code)

    def test_should_handle_sync_failure(self):
        # Given/When
        with self.logged_in('punchagan'):
            response = self.app.post(
                '/manage', data={'full_name': 'punchagan/foo'}
            )

        # Then
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            messages.NO_SUCH_REPO_FOUND, json.loads(response.data)['message']
        )

    def test_should_get_status(self):
        # When
        response = self.app.get('/status')

        # Then
        self.assertIn('GitHub Status', response.data)
        self.assertIn('Travis Status', response.data)

    def test_should_show_faq(self):
        # When
        response = self.app.get('/faq')

        # Then
        self.assertEqual(200, response.status_code)

    def test_should_show_only_username_when_printed(self):
        # Given
        fred = statiki.User('fred', GH_TOKEN)

        # /When
        # with statiki.app.test_request_context():
        user_str = '%s' % fred

        self.assertEqual("<User 'fred'>", user_str)

    #### Private protocol #####################################################

    @contextmanager
    def logged_in(self, login='fred', travis_user=True):
        """ A context manager to do stuff, while logged in as fred. """

        response           = Response()
        response._content  = json.dumps(
            dict(id=12345, login=login, name='Fred')
        )
        data               = Mock()
        data.get           = Mock(return_value=response)
        data.access_token  = GH_TOKEN

        true               = Mock(return_value=True)

        if travis_user:
            travis_patch = patch(
                'travis_utils.TravisUtils.is_travis_user', true
            )
            travis_patch.start()

        with patch('statiki.github', Mock(spec=OAuth2Service)) as gh:
            gh.get_auth_session = Mock(return_value=data)

            try:
                yield self.app.get('/authorized?code="bazooka"')

            finally:
                if travis_user:
                    travis_patch.stop()

                self.app.get('/logout')


if __name__ == '__main__':
    unittest.main()
