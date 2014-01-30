[![Build Status](https://travis-ci.org/punchagan/statiki.png?branch=master)](https://travis-ci.org/punchagan/statiki)


statiki
=======

statiki is an easy-to-use service for deploying simple web-sites.

statiki gives you a simple and elegant work-flow to build, deploy and
manage your websites and blogs.  By simple web-sites, we mean any
static sites that are created using a static site generator like
Nikola.  (Or Pelican, Jekyll, OctoPress or any of the
[hundreds of static site generators](http://staticsitegenerators.net/)
or just plain html!)

statiki aims to leverage the power of open-source and free services,
while reducing the *shit* that you have to do, to set it all
up. statiki seamlessly integrates hosting a website on GitHub using
Nikola to build the content, and Travis-CI to deploy it on GitHub
pages.

The name statiki is combination of static (from static-sites) and iki
(a Japanese aesthetic ideal that roughly means chic, stylish)

## How-to use statiki ##

1. Create an account on GitHub, if you don't have one.
2. Login/sign up on statiki's home page.
3. Sign-up to travis-ci using your GitHub credentials
4. Choose one of the following urls for create your site::

    `http://<username>.github.io` OR `http://<username>.github.io/<reponame>`

5. Click Go!

    statiki will create the appropriate repositories in your GitHub
    account.  It uses Nikola by default to create your site.

    To configure your site, click on the advanced button.  You can
    choose the static site generator to use, and make any changes to
    the configuration, etc.

6. Get redirected to the newly created site!

    This may take a while to be created.

7. All future posts can be made using GitHub's UI, or something like
   prose.io or simply using git!.

## Current Status ##

Currently, `statiki` can only enable automatic publishing for URLs like
`http://<username>.github.io/<reponame>`.  Existing repositories,
can also be managed by statiki (if they don't already have a .travis.yml file)

Statiki initialized a demo nikola site (checks for conf.py if the repository
is an old, existing one), and publishes the output.

Test site runs [here](http://muse-amuse.in:5000)

### TO-DO ###

1. Redirect to the newly created site on success, or atleast display link
1. Allow repos in organizations
1. Add tests for the bash script.
1. Clean-up the README added to the sites. Add a build status on the README!
1. See if Travis signup can be automated.
1. Display the above how-to steps, elegantly on the site!
1. Check timezone related issues?  For now, enable FUTURE_IS_NOW!
1. Add a FAQ with links to GH pages, Travis CI docs. (CNAME, [skip ci], etc.)
1. Add a status page that aggregates GH & Travis's status. ;)
