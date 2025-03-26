# Information for the developer

## Checking for vulnerabilities

I used to have `safety` for that. But it requires authentication now and worse, the authentication is not working. I am now switching to `pip-audit`:

```bash
poetry run pip-audit
```

## Running the unit tests and checking for coverage

The script `./coverage.sh` will run the unit tests and produce an HTML coverage report to be investigated in a browser from `./htmlcov/index.html`.
