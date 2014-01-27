from contextlib import contextmanager
import unittest
import json
import tempfile
import os

from mock import Mock, patch
from rauth.service import OAuth2Service
from requests import Response


import statiki


class StatikiTestCase(unittest.TestCase):

    def setUp(self):
        self.db_path = tempfile.mktemp(suffix='.db')
        statiki.app.config['SQLALCHEMY_DATABASE_URI'] = (
            'sqlite:///%s' % self.db_path
        )
        statiki.app.config['TESTING'] = True
        statiki.db.create_all()
        self.app = statiki.app.test_client()

    def tearDown(self):
        os.unlink(self.db_path)

    def test_index(self):
        # When
        response = self.app.get('/')

        # Then
        self.assertEqual(200, response.status_code)
        self.assertIn('GitHub Login', response.data)

    def test_login_should_redirect_to_authorize(self):
        # When
        response = self.app.get('/login')

        # Then
        self.assertEqual(302, response.status_code)
        self.assertIn(statiki.AUTHORIZE_URL, response.data)

    def test_should_return_to_login_not_authorized(self):
        # When
        response = self.app.get('/authorized')
        next_response = self.app.get()

        # Then
        self.assertEqual(302, response.status_code)
        self.assertIn('<a href="/">/</a>', response.data)
        self.assertIn('You did not authorize', next_response.data)

    def test_should_return_to_login_on_authorized(self):
        # Given
        with self.logged_in_as_fred() as response:
            # When
            next_response = self.app.get()

        # Then
        self.assertEqual(302, response.status_code)
        self.assertIn('<a href="/">/</a>', response.data)
        self.assertIn('Logged in as Fred', next_response.data)
        self.assertIn('Logout', next_response.data)

    def test_logout_should_redirect_to_index(self):
        # Given
        with self.logged_in_as_fred():

            # When
            response = self.app.get('/logout')
            next_response = self.app.get()

        # Then
        self.assertEqual(302, response.status_code)
        self.assertIn('GitHub Login', next_response.data)

    def test_should_ask_for_repo_name(self):
        # Given
        with self.logged_in_as_fred():

            # When
            response = self.app.get('/manage')

        # Then
        self.assertEqual(200, response.status_code)
        self.assertIn('Need a valid repository name', response.data)

    def test_should_show_travis_signup(self):
        # Given
        with self.logged_in_as_fred():

            # When
            response = self.app.get('/manage?repo=punchagan/statiki')

        # Then
        self.assertEqual(200, response.status_code)
        self.assertIn('You do not have a travis account', response.data)

    def test_should_inform_invalid_repository(self):
        # Given
        with self.logged_in_as_fred():
            with patch('statiki.is_travis_user', Mock(return_value=True)):

                # When
                response = self.app.get('/manage?repo=foobar/foobarbaz')

        # Then
        self.assertEqual(200, response.status_code)
        self.assertIn('No such repository', response.data)

    def test_should_inform_new_repository_sync_fails(self):
        # Given
        sync = Response()
        sync._content = json.dumps(dict(result=True))
        sync.status_code = 200

        user = Response()
        user._content = json.dumps(dict(is_syncing=True))
        user.status_code = 200

        with self.logged_in_as_fred():
            with patch('statiki.is_travis_user', Mock(return_value=True)):
                with patch('requests.post', Mock(return_value=sync)):
                    with patch('requests.get', Mock(return_value=user)):
                        response = self.app.get('/manage?repo=baali/svms')

        # Then
        self.assertEqual(200, response.status_code)
        self.assertIn('run a sync', response.data.lower())

    def test_should_inform_new_repository_sync_succeeds(self):
        # Given
        sync = Response()
        sync._content = json.dumps(dict(result=True))
        sync.status_code = 200

        user = Response()
        user._content = json.dumps(dict(is_syncing=False, synced_at='xxx'))
        user.status_code = 200

        with self.logged_in_as_fred():
            with patch('requests.post', Mock(return_value=sync)):
                with patch('requests.get', Mock(return_value=user)):

                    # When
                    response = self.app.get('/manage?repo=baali/svms')

        # Then
        self.assertEqual(200, response.status_code)
        self.assertIn('run a sync', response.data.lower())

    def test_should_inform_new_repository_sync_cannot_start(self):
        # Given
        with self.logged_in_as_fred():
            with patch('statiki.is_travis_user', Mock(return_value=True)):

                # When
                response = self.app.get('/manage?repo=baali/svms')

        # Then
        self.assertEqual(200, response.status_code)
        self.assertIn('run a sync', response.data.lower())

    def test_should_inform_new_repository_post_sync_fails(self):
        # Given
        sync = Response()
        sync._content = json.dumps(dict(result=True))
        sync.status_code = 200

        user = Response()
        user._content = json.dumps(dict(is_syncing=False))
        user.status_code = 200

        with self.logged_in_as_fred():
            with patch('statiki.is_travis_user', Mock(return_value=True)):
                with patch('requests.post', Mock(return_value=sync)):
                    response = self.app.get('/manage?repo=baali/svms')

        # Then
        self.assertEqual(200, response.status_code)
        self.assertIn('run a sync', response.data.lower())

    def test_should_enable_publishing(self):
        # Given
        return_true = Mock(return_value=True)
        with self.logged_in_as_fred():
            with patch('statiki.is_travis_user', return_true):
                with patch('statiki.enable_ci_for_repo', return_true):
                    with patch('statiki.create_travis_files', return_true):
                        # When
                        response = self.app.get('/manage?repo=punchagan/statiki')

        # Then
        self.assertEqual(200, response.status_code)
        self.assertIn('success', response.data.lower())

    def test_should_not_enable_publishing_without_travis_token(self):
        # Given
        return_true = Mock(return_value=True)
        with self.logged_in_as_fred():
            with patch('statiki.is_travis_user', return_true):
                # When
                response = self.app.get('/manage?repo=punchagan/statiki')

        # Then
        self.assertEqual(200, response.status_code)
        self.assertIn('failed to enable publishing', response.data.lower())

    def test_should_not_enable_publishing_unauthorized(self):
        # Given
        return_true = Mock(return_value=True)
        with self.logged_in_as_fred():
            with patch('statiki.is_travis_user', return_true):
                with patch('statiki.get_travis_access_token', return_true):
                    # When
                    response = self.app.get('/manage?repo=punchagan/statiki')

        # Then
        self.assertEqual(200, response.status_code)
        self.assertIn('failed to enable publishing', response.data.lower())

    def test_should_create_travis_files_when_non_existent(self):
        # Given
        return_true = Mock(return_value=True)
        return_false = Mock(return_value=False)

        with self.logged_in_as_fred():
            with patch('statiki.is_travis_user', return_true):
                with patch('statiki.enable_ci_for_repo', return_true):
                    with patch('statiki.github_path_exists', return_false):
                        # When
                        response = self.app.get(
                            '/manage?repo=punchagan/experiri'
                        )

        # Then
        self.assertEqual(200, response.status_code)
        self.assertIn('success', response.data.lower())

    def test_github_path_exists(self):
        # Given
        repo = 'punchagan/experiri'
        path = 'README.org'

        # When/Then
        self.assertTrue(statiki.github_path_exists(repo, path))

    #### Private protocol #####################################################

    @contextmanager
    def logged_in_as_fred(self):
        """ A context manager to do stuff, while logged in as fred. """

        response           = Response()
        response._content  = json.dumps(
            dict(id=12345, login='fred', name='Fred')
        )
        data               = Mock()
        data.get           = Mock(return_value=response)
        data.access_token  = 'foo bar baz'

        with patch('statiki.github', Mock(spec=OAuth2Service)) as gh:
            gh.get_auth_session = Mock(return_value=data)

            yield self.app.get('/authorized?code="bazooka"')

        self.app.get('/logout')


if __name__ == '__main__':
    unittest.main()
