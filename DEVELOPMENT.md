# Information for the developer

## Checking for vulnerabilities

I used to have `safety` for that. But it requires authentication now and worse, the authentication is not working. I am now switching to `pip-audit`:

```bash
poetry run pip-audit
```

## Running the unit tests and checking for coverage

The script `./coverage.sh` will run the unit tests and produce an HTML coverage report to be investigated in a browser from `./htmlcov/index.html`.

## Releasing a new version

The CI configured with GitHub Actions will not release a new version of RedisCache. This has to be done manually with the help of the `./publish.sh` script.

Deployment procedure:

- Create a `./secrets.sh` that will export the `PYPI_API_TOKEN` environment variable with your Pypi API token that is allowed to deploy a new version of RedisCache.
- Create the new version number with a `poetry version` command see `poetry version --help` for details. To simply go to the next patch version, use `poetry version patch`. This is also the default behavior.
- Make sure all you changes are pushed to the GitHub repository, merged to `main` and that you are also locally in branch `main`.
- Run the `./publish.sh` script.
