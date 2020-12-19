#!/usr/bin/env bash

source venv/bin/activate

coverage run --source=rediscache --module pytest "$@"
coverage report --show-missing
