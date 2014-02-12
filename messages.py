# -*- coding: utf-8 -*-

# Copyright © 2014 Puneeth Chaganti and others.
# See the LICENSE file for license rights and limitations (MIT).

AUTH_DECLINED = 'You did not authorize the request'

CREATE_REPO_FAILURE = (
    'Failed to create your repository. Try again, or get in touch with us!'
)

CREATE_REPO_SUCCESS = 'Repository created ... '

DONE = (
    'Congratulations! Your site will be published to <a href="'
    'http://%(USER)s.github.io/%(REPO)s">http://%(USER)s.github.io/%(REPO)s'
    '</a> in a few minutes...  Grab a cup of coffee, while the internet '
    'works for you!'
)

NO_SUCH_REPO_FOUND = (
    'Repo could not be found. Run a sync, <a href='
    '"http://travis-ci.org/profile" target="_blank">manually?</a>'
)

NO_TRAVIS_ACCOUNT = (
    'Please <a href="https://travis-ci.org/profile" target="_blank">signup</a>'
    ' for a Travis-ci account to proceed.  If you have just signed up, please'
    ' wait for Travis to sync your repositories from GitHub.'
)

ONLY_HOOKS_ENABLED = (
    'Only the travis ci integration was successfully completed.  Creation of '
    '.travis.yml and travis_build_n_deploy.sh failed.  Do they already exist?'
    'If so, your site should be published in a few minutes to'
    'http://%(USER)s.github.io/%(REPO)s">http://%(USER)s.github.io/%(REPO)s'
    'Otherwise, try submitting your request, again or contact us!'
)

OVERWRITE_YAML = (
    'Your project already seems to have a .travis.yml file. Do you wish to '
    'overwrite it?'
)

REPO_EXISTS = 'The repository you specified, already exists.'

TOTAL_FAILURE = (
    'Failed to setup travis integration, or commit required files to the repo!'
    ' This is a total failure!  Try resubmitting your request, or contact us!'
)
