#!/usr/bin/env bash

poetry install

poetry run coverage run --source=rediscache --module pytest "$@"
poetry run coverage report --show-missing
