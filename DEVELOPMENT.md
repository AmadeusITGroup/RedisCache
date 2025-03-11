# Information for the developer

## Checking for vulnerabilities

I used to have `safety` for that. But it requires authentication now and worse, the authentication is not working. I am now switching to `pip-audit`:

```bash
poetry run pip-audit
```
