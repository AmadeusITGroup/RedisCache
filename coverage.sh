#!/usr/bin/bash

# Run the unit tests and generate the coverage HTML report

poetry run pytest --cov=rediscache --cov-fail-under=100

poetry run coverage html
