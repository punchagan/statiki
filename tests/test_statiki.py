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
        statiki.render_readme()
        self.app = statiki.app.test_client()

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_render_readme(self):
        # Given
        readme = join(abspath(statiki.app.template_folder), 'readme.html')
        if exists(readme):
            os.unlink(readme)

        # When
        self.app.get('/readme')

        # Then
        self.assertTrue(exists(readme))

    def test_should_create_travis_files(self):
        # Given
        expected ={
            statiki.SCRIPT: True,
            '.travis.yml': True
        }

        # When
        with patch('github_utils.GitHubUtils.commit', Mock(return_value=True)):
            created = statiki.create_travis_files(THIS_REPO, GH_TOKEN)

        # Then
        self.assertDictEqual(expected, created)

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

    def test_should_partial_success(self):
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
            response = self.app.post('/manage', data=dict(repo_name='statiki'))

        # Then
        self.assertEqual(200, response.status_code)
        self.assertIn(json.dumps(messages.NO_TRAVIS_ACCOUNT), response.data)

    def test_should_request_repo_name(self):
        # Given/When
        with self.logged_in():
            response = self.app.post('/manage')

        # Then
        self.assertEqual(200, response.status_code)
        self.assertIn(messages.EMPTY_REPO_NAME, response.data)

    def test_should_create_repo_but_sync_fails(self):
        # Given
        target = 'github_utils.GitHubUtils.create_new_repository'

        # When/Then
        with self.logged_in('punchagan'):
            with patch(target, Mock()) as create:
                self.app.post('/manage', data={'repo_name': 'foo'})

        # Then
        args, _ = create.call_args
        self.assertEqual(args, ('punchagan/foo', GH_TOKEN))

    def test_should_manage_this_repo(self):
        # Given
        target = 'travis_utils.TravisUtils.get_repo_id'

        # When/Then
        with self.logged_in('punchagan'):
            with patch(target, Mock(return_value=1779263)):
                response = self.app.post(
                    '/manage', data={'repo_name': 'statiki'}
                )

        # Then
        self.assertEqual(200, response.status_code)

    def test_should_get_status(self):
        # When
        response = self.app.get('/status')

        # Then
        self.assertIn('GitHub Status', response.data)
        self.assertIn('Travis Status', response.data)

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

            yield self.app.get('/authorized?code="bazooka"')

        if travis_user:
            travis_patch.stop()

        self.app.get('/logout')


if __name__ == '__main__':
    unittest.main()
