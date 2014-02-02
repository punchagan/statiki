import os
from mock import Mock, patch
import unittest

from travis_utils import TravisUtils
import yaml

def get_gh_token(bogus):
    """ Returns the GH token to use. """
    # fixme: Change this to check if we are rate limited, an use BOGUS if so.

    token = os.environ.get('GH_TOKEN', bogus)

    return token

BOGUS = 'this-is-a-bogus-token'
THIS_REPO = 'punchagan/statiki'
GH_TOKEN = get_gh_token(BOGUS)
TRAVIS_TOKEN = (
    BOGUS if GH_TOKEN == BOGUS else
    TravisUtils.get_access_token(GH_TOKEN)
)


@unittest.skipIf(TRAVIS_TOKEN == BOGUS, 'Need a real GitHubtoken...')
class TestTravisUtils(unittest.TestCase):

    def test_should_find_existing_hook(self):
        self.assertTrue(
            TravisUtils.hook_exists(THIS_REPO, TRAVIS_TOKEN)
        )

    def test_should_not_find_bogus_hook(self):
        self.assertFalse(
            TravisUtils.hook_exists(THIS_REPO+BOGUS, TRAVIS_TOKEN)
        )

    def test_should_not_find_hooks_unauthenticated(self):
        self.assertFalse(
            TravisUtils.hook_exists(THIS_REPO+BOGUS, BOGUS)
        )

    def test_should_get_public_key(self):
        # When
        key = TravisUtils.get_public_key(THIS_REPO)

        # Then
        self.assertIn('BEGIN PUBLIC KEY', key)

    def test_should_confirm_travis_user(self):
        # Given
        token_mock = Mock(return_value=TRAVIS_TOKEN)

        # When
        with patch('travis_utils.TravisUtils.get_access_token', token_mock):
            token = TravisUtils.is_travis_user(GH_TOKEN)

        # Then
        self.assertEqual(token, TRAVIS_TOKEN)

    def test_should_detect_bogus_user(self):
        self.assertIsNone(TravisUtils.is_travis_user(BOGUS))

    def test_should_get_repo_id(self):
        # Given
        full_name = THIS_REPO
        repo_id   = 1779263

        # When
        id = TravisUtils.get_repo_id(full_name, TRAVIS_TOKEN)

        # Then
        self.assertEqual(id, repo_id)

    def test_should_not_get_bogus_repo_id(self):
        # Given
        full_name = THIS_REPO + BOGUS

        # When
        id = TravisUtils.get_repo_id(full_name, TRAVIS_TOKEN)

        # Then
        self.assertIsNone(id)

    def test_should_enable_hook(self):
        # Given
        repo_id = TravisUtils.get_repo_id(THIS_REPO, TRAVIS_TOKEN)

        # When
        enabled = TravisUtils.enable_hook(repo_id, TRAVIS_TOKEN)

        # Then
        self.assertTrue(enabled)

    def test_should_encrypt_text(self):
        # Given
        data = 'this is super secret'

        # When/Then
        TravisUtils.get_encrypted_text(THIS_REPO, data)
        # No idea what to test!  This test just checks for runtime errors.

    def test_should_get_yaml_contents(self):
        # When
        contents = TravisUtils.get_yaml_contents(THIS_REPO, GH_TOKEN)

        # Then
        data = yaml.load(contents)
        self.assertIn('install', data)
        self.assertIn('script', data)
        self.assertIn('secure', data['env']['global'])

    def test_should_get_script_contents(self):
        # Given
        expected = 'REPO=%s' % THIS_REPO

        # When
        contents = TravisUtils.get_script_contents(THIS_REPO)

        # Then
        self.assertIn(expected, contents)

    def test_should_not_start_sync_unauthenticated(self):
        self.assertFalse(TravisUtils.sync_with_github(BOGUS))

    def test_should_sync(self):
        # Given
        true = Mock(return_value=True)
        json = Mock(return_value={'is_syncing': False})
        response = Mock(status_code=200, json=json)

        # When
        with patch('travis_utils.TravisUtils.start_sync', true):
            with patch('requests.get', Mock(return_value=response)):
                synced = TravisUtils.sync_with_github(TRAVIS_TOKEN)

        # Then
        self.assertTrue(synced)

    def test_should_handle_sync_timeout(self):
        # Given
        true = Mock(return_value=True)
        json = Mock(return_value={'is_syncing': True})
        response = Mock(status_code=200, json=json)

        # When
        with patch('travis_utils.TravisUtils.start_sync', true):
            with patch('requests.get', Mock(return_value=response)):
                with patch('time.sleep', Mock()):
                    synced = TravisUtils.sync_with_github(TRAVIS_TOKEN)

        # Then
        self.assertFalse(synced)

    def test_should_handle_aborted_sync(self):
        # Given
        true = Mock(return_value=True)
        response = Mock(status_code=404)

        # When
        with patch('travis_utils.TravisUtils.start_sync', true):
            with patch('requests.get', Mock(return_value=response)):
                synced = TravisUtils.sync_with_github(TRAVIS_TOKEN)

        # Then
        self.assertFalse(synced)
