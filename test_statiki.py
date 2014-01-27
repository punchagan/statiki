import unittest
import json

from rauth.service import OAuth2Service
from requests import Response
import mock

import statiki


class StatikiTestCase(unittest.TestCase):

    def setUp(self):
        statiki.app.config['TESTING'] = True
        self.app = statiki.app.test_client()

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
        statiki.github                  = mock.Mock(spec=OAuth2Service)
        response                        = Response()
        response._content               = json.dumps(
            dict(id=12345, login='fred', name='Fred')
        )
        data                            = mock.Mock()
        data.get                        = mock.Mock(return_value=response)
        data.access_token               = 'foo bar baz'
        statiki.github.get_auth_session = mock.Mock(return_value=data)

        # When
        response = self.app.get('/authorized?code="bazooka"')
        next_response = self.app.get()

        # Then
        self.assertEqual(302, response.status_code)
        self.assertIn('<a href="/">/</a>', response.data)
        self.assertIn('Logged in as Fred', next_response.data)


if __name__ == '__main__':
    unittest.main()
