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
   # fixme: can this be automated out?
4. Choose one of the following urls for create your site::

    `http://<username>.github.io` OR `http://<username>.github.io/<reponame>`

5. Click create.

    statiki will create the appropriate repositories in your GitHub
    account.  It uses Nikola by default to create your site.

    To configure your site, click on the advanced button.  You can
    choose the static site generator to use, and make any changes to
    the configuration, etc.

6. Get redirected to the newly created site!

    This may take a while to be created.

7. All future posts can be made using GitHub's UI, or something like
   prose.io or simply using git!.


#### Notes & References ####

- Remember to add a .nojekyll file.
- Add links for documentation to Github pages, for various things like CNAME.
- Add links to Travis-ci docs atleast for skip-ci stuff.
- http://about.travis-ci.org/docs/user/deployment/custom/
- http://awestruct.org/auto-deploy-to-github-pages/
- FUTURE_IS_NOW mess-ups. Dates and timezone issues
- Add a build status on the README!
