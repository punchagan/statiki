# -*- coding: utf-8 -*-

""" A fabric file for deploying the site from TravisCI. """

import os

from fabric.api import local, settings


DATA = {}


def build_and_deploy():
    """ Build and deploy the output. """

    _create_output_branch()
    _build_html()
    _git_commit_all()
    _git_push(_get_output_branch())


def git_config_setup():
    """ Setup git for pushing from Travis. """

    local('git config user.email $GIT_EMAIL')
    local('git config user.name $GIT_NAME')

    local(
        'git remote set-url --push origin '
        'https://$GH_TOKEN@github.com/$TRAVIS_REPO_SLUG.git'
    )


def init_site():
    """ Initialize a nikola demo site. """

    from nikola.plugins.command.init import CommandInit

    i = CommandInit()
    i.SAMPLE_CONF['SITE_URL'] = _get_site_url()
    i.SAMPLE_CONF.update(DATA)
    i.execute({'demo': True}, ['demo'])

    local('mv demo/* . && rmdir demo')
    local('touch files/.nojekyll')


def populate_source():
    """ Populate the source branch with a demo site. """

    if os.path.exists('conf.py'):
        return

    branch = _get_source_branch()

    local('git checkout %s' % branch)
    init_site()
    _git_commit_all()
    _git_push(branch)


def main():
    """ Main script to kick off the deployment. """

    if not os.environ.get('TRAVIS_PULL_REQUEST', 'false') == 'false':
        return

    git_config_setup()
    populate_source()
    build_and_deploy()


#### Private protocol #########################################################

def _build_html():
    """ Run the build command and get rid of everything else. """

    # Build twice until getnikola/nikola#1032 is fixed.
    local('nikola build && nikola build')

    ## Remove all the source files, we only want the output!
    local('ls | grep -v output | xargs rm -rf')
    local('mv output/* .')


def _create_output_branch():
    branch = _get_output_branch()

    with settings(warn_only=True):
        local('git branch -D %s' % branch)

    local('git checkout --orphan %s' % branch)


def _get_source_branch():
    return 'deploy' if _user_pages() else 'master'


def _get_output_branch():
    return 'master' if _user_pages() else 'gh-pages'


def _get_repo_name():
    repo_slug = os.environ.get('TRAVIS_REPO_SLUG', '/')
    user, repo = repo_slug.split('/')
    return user, repo


def _get_site_url():
    user, repo = _get_repo_name()
    if _user_pages():
        site_url = 'http://%s.github.io/' % user

    else:
        site_url = 'http://%s.github.io/%s' % (user, repo)

    return site_url


def _git_commit_all():
    """ Commit all the changes to the repo. """

    # Remove deleted files
    result = local('git ls-files --deleted -z', capture=True)
    for path in result.split('\x00'):
        if len(path.strip()) > 0:
            local('git rm %s' % path, capture=True)

    # Add new files
    local('git add .', capture=True)

    # Commit
    with settings(warn_only=True):
        local('git commit -m "$(date)"')


def _git_push(branch):
    """ Push any changes, to the specified branch. """

    local(
        'git push -f origin %(branch)s:%(branch)s' % {'branch': branch},
        capture=True
    )
    print('Pushed to %s' % branch)


def _user_pages():
    user, repo = _get_repo_name()

    if repo.startswith(user) and repo.endswith(('github.io', 'github.com')):
        user_pages = True

    else:
        user_pages = False

    return user_pages
