set -e

# Build
nikola build

# Setup git for pushing from Travis
## Setup user details, so commits etc work.
git config user.email $GIT_EMAIL
git config user.name $GIT_NAME
## Change the remote url using the token
git remote set-url --push origin https://$GH_TOKEN@github.com/%(REPO)s.git

# Commit the Build output
## Create a new gh-pages branch
git branch -D gh-pages || true
git checkout --orphan gh-pages
## Remove all the source files, we only want the output!
ls | grep -v output | xargs rm -rf
mv output/* .
## Remove deleted files
git ls-files --deleted -z | xargs -0 git rm >/dev/null 2>&1
## Add new files
git add . >/dev/null 2>&1
## Commit
git commit -m "$(date)"

# Push!
git push -f origin gh-pages:gh-pages >/dev/null 2>&1
