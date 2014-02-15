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
    'overwrite it, with these contents?'
)

REPO_EXISTS = (
    'The repository you specified, already exists. Statiki will add the '
    'following files to your repository. Continue?'
)

TOTAL_FAILURE = (
    'Failed to setup travis integration, or commit required files to the repo!'
    ' This is a total failure!  Try resubmitting your request, or contact us!'
)

TUTORIAL_STEPS = [
    {
        'title': (
            'Create an account on <a href="https://github.com/join" '
            'target="_blank">GitHub</a>'
        ),
        'description': (
            '<p> If you already have one, login. Statiki uses GitHub OAuth '
            'to authenticate.</p>'
        )
    },

    {
        'title': (
            'Create an account on <a href="https://travis-ci.org/profile" '
            'target="_blank">TravisCI</a>'
        ),
        'description': (
            '<p>TravisCI also uses GitHub OAuth. Once you create your account,'
            ' wait for Travis to sync your repositories from GitHub </p>'
        )
    },

    {
        'title': (
            'Create an account on <a href="/login" target="_blank">Statiki</a>'
        ),
        'description': (
            '<p>Statiki only uses your authentication to manage the '
            'repositories you specify. Once your repository has been '
            'successfully setup, you can safely '
            '<a href="//github.com/settings/applications" target="_blank">'
            'revoke access</a> (recommended).</p>'
        )
    },

    {
        'title': 'Choose a URL and Go!',
        'description': (
            '<p>Currently, only urls starting with <code>'
            'http://&lt;username&gt;.github.io/</code> are supported. '
            'In future, repositories in organizations may be supported</p>'
            '<p><em>NOTE: RSS feeds/Galleries may not work correctly, '
            'due to an issue in Nikola.</em> </p>'
        )
    },

    {
        'title': 'Profit!',
        'description': (
            '<p>Your site should be ready in a few minutes. You will be '
            'notified by a successful build notification from TravisCI</p>'
            '<p><em>(Actual time depends on the availability of TravisCI '
            'and how long GitHub takes to deploy your pages.)</em></p>'
            '<p> You can edit your site either using the web-editor on GitHub,'
            ' or edit using your favorite editor and push the changes </p>'
        )
    },

]
