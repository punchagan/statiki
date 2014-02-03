set -e

REPO=%(REPO)s

# Run the build command and get rid of everything else.
function build_html() {
    # Build
    nikola build

    ## Remove all the source files, we only want the output!
    ls | grep -v output | xargs rm -rf
    mv output/* .
}

# Push the built html to github pages
function deploy_html() {

    git_create_gh_pages
    build_html
    git_commit_all
    git_push_silent gh-pages

}

# Push to the specified branch
function git_push_silent() {

    # Push!
    git push -f origin $1:$1 >/dev/null 2>&1
    echo "Pushed to $1"
}

# Commit all the files in the current repository
function git_commit_all() {
    set +e

    # Remove deleted files
    git ls-files --deleted -z | xargs -0 git rm >/dev/null 2>&1

    # Add new files
    git add . >/dev/null 2>&1

    # Commit
    git commit -m "$(date)"

    set -e
}

# Setup git for pushing from Travis
function git_config_setup() {

    git config user.email $GIT_EMAIL
    git config user.name $GIT_NAME

    git remote set-url --push origin https://$GH_TOKEN@github.com/$REPO.git
}


function git_create_gh_pages() {
    ## Create a new gh-pages branch
    git branch -D gh-pages || true
    git checkout --orphan gh-pages
}

# Fix the config file
# In future, should let users choose an theme, etc!
function fix_nikola_config(){

    GH_USER=`echo $REPO | cut -d "/" -f 1`
    REPO_NAME=`echo $REPO | cut -d "/" -f 2`
    sed -i 's$^SITE_URL.*$SITE_URL = "http://'$GH_USER'.github.io/'$REPO_NAME'"$g' conf.py

}

# Initialize site using nikola's sample site
function initialize_site() {

    git checkout master
    nikola init --demo demo
    mv demo/* .
    touch files/.nojekyll
    fix_nikola_config
    git_commit_all
    git_push_silent master

}

# Run only if not a pull request.
if [[ $TRAVIS_PULL_REQUEST == 'false' ]] ; then
    git_config_setup

    if [[ ! -f conf.py ]]; then
        initialize_site
    fi

    deploy_html

fi
