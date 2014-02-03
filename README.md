[![Build Status](https://travis-ci.org/punchagan/statiki.png?branch=master)](https://travis-ci.org/punchagan/statiki)
[![Coverage Status](https://coveralls.io/repos/punchagan/statiki/badge.png?branch=master)](https://coveralls.io/r/punchagan/statiki?branch=master)

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

## Current Status ##

Currently, `statiki` can only enable automatic publishing for URLs like
`http://<username>.github.io/<reponame>`.  Existing repositories,
can also be managed by statiki (if they don't already have a .travis.yml file)

Statiki initializes a demo nikola site (checks for conf.py if the repository
is an old, existing one), and publishes the output.

Runs at [http://statiki.muse-amuse.in](http://statiki.muse-amuse.in)

### TO-DO ###

1. Allow repos in organizations
1. Allow user/organization pages
1. Allow plugin and theme installation
1. Fix RSS issues when deploying to subdirs or work around it
1. Clean-up the README added to the sites. Add a build status on the README!
1. See if Travis signup can be automated.
1. Check timezone related issues?  For now, enable FUTURE_IS_NOW!
1. Add a FAQ with links to GH pages, Travis CI docs. (CNAME, [skip ci], etc.)
1. Add javascript tests?
1. Add tests for the bash script?
