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


class StatikiTestCase(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.db_path = join(self.tempdir, 'test.db')
        statiki.app.config['SQLALCHEMY_DATABASE_URI'] = (
            'sqlite:///%s' % self.db_path
        )
        statiki.app.config['TESTING'] = True
        statiki.db.create_all()
        statiki.render_readme()
        self.app = statiki.app.test_client()

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_index(self):
        # When
        response = self.app.get('/')

        # Then
        self.assertEqual(200, response.status_code)
        self.assertIn(statiki.DESCRIPTION, response.data)

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
        self.assertIn(messages.AUTH_DECLINED, next_response.data)

    def test_should_return_to_login_on_authorized(self):
        # Given
        with self.logged_in_as_fred() as response:
            # When
            next_response = self.app.get()

        # Then
        self.assertEqual(302, response.status_code)
        self.assertIn('<a href="/">/</a>', response.data)
        self.assertIn('Logout', next_response.data)

    def test_logout_should_redirect_to_index(self):
        # Given
        with self.logged_in_as_fred():

            # When
            response = self.app.get('/logout')
            next_response = self.app.get()

        # Then
        self.assertEqual(302, response.status_code)
        self.assertIn(statiki.DESCRIPTION, next_response.data)

    def test_should_show_travis_signup(self):
        # Given
        with self.logged_in_as_fred():

            # When
            response = self.app.post('/manage', data=dict(repo_name='statiki'))

        # Then
        self.assertEqual(200, response.status_code)
        self.assertIn(json.dumps(messages.NO_TRAVIS_ACCOUNT), response.data)

    def test_should_request_repo_name(self):
        # Given
        with self.logged_in_as_fred():
            with patch('statiki.is_travis_user', Mock(return_value=True)):

                # When
                response = self.app.post('/manage')

        # Then
        self.assertEqual(200, response.status_code)
        self.assertIn(messages.EMPTY_REPO_NAME, response.data)

    def test_should_create_repo(self):
        # Given
        def create(*args, **kwargs):
            raise RuntimeError(*args, **kwargs)

        # When/Then
        with self.logged_in_as_fred():
            with patch('statiki.is_travis_user', Mock(return_value=True)):
                with patch('statiki.is_valid_repo', Mock(return_value=False)):
                    with patch('statiki.create_new_repository', create):
                        with self.assertRaises(RuntimeError) as e:
                            self.app.post('/manage', data={'repo_name': 'foo'})

        # Then
        self.assertEquals(e.exception.args, ('punchagan/foo', 'foo bar baz'))

    def test_should_create_and_manage_repo(self):
        # Given
        true = Mock(return_value=True)
        files = Mock(return_value={'.travis.yml': True})

        # When
        with self.logged_in_as_fred():
            with patch('statiki.is_travis_user', true):
                with patch('statiki.is_valid_repo', true):
                    with patch('statiki.get_repo_id', true):
                        with patch('statiki.enable_ci_for_repo', true):
                            with patch('statiki.create_travis_files', files):
                                response = self.app.post(
                                    '/manage', data={'repo_name': 'X'}
                                )

        # Then
        self.assertEqual(200, response.status_code)
        self.assertTrue(json.loads(response.data)['success'])

    def test_should_inform_new_repository_sync_fails(self):
        # Given
        sync = Response()
        sync._content = json.dumps(dict(result=True))
        sync.status_code = 200

        user = Response()
        user._content = json.dumps(dict(is_syncing=True))
        user.status_code = 200

        true = Mock(return_value=True)

        # When
        with self.logged_in_as_fred():
            with patch('statiki.is_travis_user', Mock(return_value=True)):
                with patch('requests.post', Mock(return_value=sync)):
                    with patch('requests.get', Mock(return_value=user)):
                        with patch('statiki.travis_hook_exists', true):
                            response = self.app.post(
                                '/manage', data={'repo_name': 'svms'}
                            )

        # Then
        self.assertEqual(200, response.status_code)
        self.assertIn(json.dumps(messages.NO_SUCH_REPO_FOUND), response.data)

    def test_should_inform_sync_fails_to_start(self):
        # Given
        sync = Response()
        sync._content = json.dumps(dict(result=True))
        sync.status_code = 404

        user = Response()
        user._content = json.dumps(dict(is_syncing=True))
        user.status_code = 200

        true = Mock(return_value=True)

        # When
        with self.logged_in_as_fred():
            with patch('statiki.is_travis_user', Mock(return_value=True)):
                with patch('requests.post', Mock(return_value=sync)):
                    with patch('requests.get', Mock(return_value=user)):
                        with patch('statiki.travis_hook_exists', true):
                            response = self.app.post(
                                '/manage', data={'repo_name': 'svms'}
                            )

        # Then
        self.assertEqual(200, response.status_code)
        self.assertIn(json.dumps(messages.NO_SUCH_REPO_FOUND), response.data)

    def test_should_inform_sync_abort(self):
        # Given
        sync = Response()
        sync._content = json.dumps(dict(result=True))
        sync.status_code = 200

        user = Response()
        user._content = json.dumps(dict(is_syncing=True))
        user.status_code = 404

        # When
        with self.logged_in_as_fred():
            with patch('statiki.is_travis_user', Mock(return_value=True)):
                with patch('statiki.is_valid_repo', Mock(return_value=True)):
                    with patch('requests.post', Mock(return_value=sync)):
                        with patch('requests.get', Mock(return_value=user)):
                            response = self.app.post(
                                '/manage', data={'repo_name': 'svms'}
                            )

        # Then
        self.assertEqual(200, response.status_code)
        self.assertIn(json.dumps(messages.NO_SUCH_REPO_FOUND), response.data)

    def test_should_inform_new_repository_sync_succeeds(self):
        # Given
        sync = Response()
        sync._content = json.dumps(dict(result=True))
        sync.status_code = 200

        user = Response()
        user._content = json.dumps(dict(is_syncing=False, synced_at='xxx'))
        user.status_code = 200

        true = Mock(return_value=True)

        with self.logged_in_as_fred():
            with patch('requests.post', Mock(return_value=sync)):
                with patch('requests.get', Mock(return_value=user)):
                    with patch('statiki.travis_hook_exists', true):
                        # When
                        response = self.app.post(
                            '/manage', data={'repo_name': 'svms'}
                        )

        # Then
        self.assertEqual(200, response.status_code)
        self.assertIn(json.dumps(messages.NO_SUCH_REPO_FOUND), response.data)

    def test_should_not_enable_hook_unauthorized(self):
        # Given
        return_true = Mock(return_value=True)

        # When
        with self.logged_in_as_fred():
            with patch('statiki.is_travis_user', return_true):
                with patch('statiki.get_travis_access_token', return_true):
                    with patch('statiki.get_repo_id', return_true):
                        response = self.app.post(
                            '/manage', data={'repo_name': 'statiki'}
                        )

        # Then
        self.assertEqual(200, response.status_code)
        self.assertIn(messages.TOTAL_FAILURE, response.data)

    def test_should_manage_existing_repo(self):
        # Given
        return_true = Mock(return_value=True)
        return_false = Mock(return_value=False)

        # When
        with self.logged_in_as_fred():
            with patch('statiki.is_travis_user', return_true):
                with patch('statiki.github_path_exists', return_false):
                    with patch('statiki.enable_ci_for_repo', return_true):
                        with patch('statiki.travis_hook_exists', return_true):
                            response = self.app.post(
                                '/manage', data={'repo_name': 'experiri'}
                            )

        # Then
        self.assertEqual(200, response.status_code)
        self.assertIn(messages.ONLY_HOOKS_ENABLED, response.data)

    def test_github_path_exists(self):
        # Given
        repo = 'punchagan/statiki'
        path = 'README.md'

        # When/Then
        self.assertTrue(statiki.github_path_exists(repo, path))

    def test_should_create_new_repository(self):
        # Given
        repo = 'foo/bar'
        response = Response()
        response.status_code = 201

        # When
        with self.logged_in_as_fred():
            with patch('requests.post', Mock(return_value=response)):
                created = statiki.create_new_repository(repo, 'foo bar baz')

        # Then
        self.assertTrue(created)

    def test_render_readme(self):
        # Given
        readme = join(abspath(statiki.app.template_folder), 'readme.html')
        if exists(readme):
            os.unlink(readme)

        # When
        self.app.get('/readme')

        # Then
        self.assertTrue(exists(readme))

    #### Private protocol #####################################################

    @contextmanager
    def logged_in_as_fred(self):
        """ A context manager to do stuff, while logged in as fred. """

        response           = Response()
        response._content  = json.dumps(
            dict(id=12345, login='punchagan', name='Fred')
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
