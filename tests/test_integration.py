# -*- coding: utf-8 -*-

# Copyright © 2014 Puneeth Chaganti and others.
# See the LICENSE file for license rights and limitations (MIT).

""" Integration tests for statiki. """

import os
from os.path import exists, join
import shlex
import shutil
import subprocess
import tempfile
import unittest

from pkg_resources import parse_version
import yaml

import statiki

TEST_REPO = 'punchagan/experiri'


class TestIntegration(unittest.TestCase):
    """ Integration tests for statiki. """

    #### 'TestCase' protocol ##################################################

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.repo_dir = self._create_github_repo()
        self.venv_dir = self._create_venv()
        self.old_cwd = os.getcwd()
        self.cache_dir = join(self.old_cwd, 'cache')
        os.chdir(self.repo_dir)
        self._activate_venv()
        self._setup_env()

        return

    def tearDown(self):
        os.chdir(self.old_cwd)
        if exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

        return

    #### Tests ####

    def test_should_run_install_steps(self):
        # Given
        install_steps = self._get_install_steps()

        # When
        for command in install_steps:
            subprocess.call(
                shlex.split(command),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )

        # Then
        nikola_version = subprocess.check_output(
            shlex.split("python -c 'import nikola; print nikola.__version__'")
        )
        self.assertGreaterEqual(cmp(parse_version(nikola_version), '6.4.0'), 0)
        self.assertEqual(
            subprocess.call(shlex.split("python -c 'import webassets'")), 0
        )

        return

    def test_should_populate_repo(self):
        # Given
        script = self._get_yaml_content()['script']
        install_steps = self._get_install_steps()
        for command in install_steps:
            subprocess.call(
                shlex.split(command),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )

        # When
        output, error = subprocess.Popen(
            shlex.split(script),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        ).communicate()

        # Then
        self.assertIn('git push', output.splitlines()[-1])
        self.assertTrue(exists(join(self.repo_dir, 'conf.py')))
        self.assertTrue(exists(join(self.repo_dir, 'files', '.nojekyll')))

        return

    #### Private protocol #####################################################

    def _activate_venv(self):
        """ Activate the venv. """

        bin_dir = join(self.venv_dir, 'bin')
        os.environ['PATH'] = '%s:%s' % (bin_dir, os.environ.get('PATH'))

        pip = subprocess.check_output(['which', 'pip'])
        assert pip.startswith(bin_dir), 'venv not activated'

        return

    def _create_github_repo(self):
        """ Create a github repository with the required files. """

        repo_dir = join(self.temp_dir, 'repo')
        subprocess.check_output(['git', 'init', repo_dir])

        content = statiki.get_travis_files_content(TEST_REPO, 'BOGUS', {})

        for info in content:
            path = join(repo_dir, info['name'])
            with open(path, 'w') as f:
                f.write(info['content'])

            subprocess.check_output(['git', 'add', path], cwd=repo_dir)
            subprocess.check_output(
                ['git', 'commit', '-m', '%s' % info['message']],  cwd=repo_dir
            )

        subprocess.check_output(
            shlex.split('git remote add origin ..'), cwd=repo_dir
        )

        return repo_dir

    def _create_venv(self):
        """ Create a venv to use for running the commands in .travis.yml. """

        venv_dir = join(self.temp_dir, 'venv')
        subprocess.check_output(['virtualenv', venv_dir])

        return venv_dir

    def _fix_install_steps(self, commands):
        """ Fix the install steps to reduce work done during tests. """

        fixed_commands = []

        for i, command in enumerate(commands[:]):
            if command.startswith('pip'):
                command += ' --download-cache=%s' % self.cache_dir
                fixed_commands.append(command)

            elif command.startswith('wget'):
                zip_file = join(self.cache_dir, 'v2.7.zip')
                command += ' -nc -O %s' % zip_file
                fixed_commands.append(command)
                fixed_commands.append('cp %s .' % zip_file)

            else:
                fixed_commands.append(command)

        return fixed_commands

    def _get_install_steps(self):
        """ Get the install steps defined in the .travis.yml. """

        content = self._get_yaml_content()

        return self._fix_install_steps(content['install'])

    def _get_yaml_content(self):
        """ Return the contents of the .travis.yml file. """

        with open('.travis.yml') as f:
            content = yaml.load(f)

        return content

    def _setup_env(self):
        """ Setup environment variables used by the fabfile. """

        os.environ['GIT_NAME'] = statiki.GIT_NAME
        os.environ['GIT_EMAIL'] = statiki.GIT_EMAIL
        os.environ['GH_TOKEN'] = 'this-is-a-bogus-token:password'
        os.environ['TRAVIS_REPO_SLUG'] = TEST_REPO

        return
