#!/usr/bin/env bash

# Check if we are on the main branch
branch=$(git branch --show-current)
if [[ $branch != "main" ]]; then
    echo "You need to be on the main branch to publish"
    exit 1
fi
# Check of everything is committed
status=$(git status --porcelain)
if [[ -n $status ]]; then
    echo "You need to commit everything before publishing"
    exit 1
fi
# Check if everything is pushed
status=$(git status -sb)
if [[ $status != "## main...origin/main" ]]; then
    echo "You need to push everything before publishing"
    exit 1
fi

# If the current version is the latest one available on PyPI, we need to bump it
pypi_version=$(poetry search rediscache | grep -oP "^rediscache\s+\(\K[0-9]+\.[0-9]+\.[0-9]+")
local_version=$(poetry version --short)
if [[ $pypi_version == $local_version ]]; then
    poetry version patch
    local_version=$(poetry version --short)
    git add pyproject.toml
    git commit -m "Bump version to ${local_version}"
    git push
fi
echo "Old PyPI version: ${pypi_version}"
echo "New local version: ${local_version}"

# Then we build the project
poetry build

# Then we publish the project
if [[ -f "secrets.sh" ]]; then
    . secrets.sh
    poetry publish --username=__token__ --password=${PYPI_API_TOKEN}
else
    echo "No secrets.sh file found"
fi

# Now we tag the repository
git tag "${local_version}"
git push --tags
