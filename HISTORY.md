# History

- 1.0.5 - 26/03/2025
  - Add a `py.typed` file to indicate mypy that RedisCache supports type checking

- 1.0.4 - 26/03/2025
  - Poetry update
  - Remove unused code
  - Google style comment of arguments of functions
  - Add coverage script
  - No more datetime.utcnow()

- 1.0.3 - 11/03/2024
  - Upgrade rediscache to not use UTC

- 1.0.2 - 11/03/2024
  - Get rid of `safety`

- 1.0.1 - 11/03/2024
  - Update dependencies
  - Start using `pip-audit`
  - Fix the `publish.sh` script

- 1.0.0 - 25/02/2024
  - No more serialization in the cache decorator
  - No need for alternate cache decorator
  - Add HISTORY file

- 0.3.3 - 25/02/2024
  - English spell check
  - Restore the function bypass lost by mistake

- 0.3.2 - 25/02/2024
  - Create a decorator help to add serialization and deserialization when needed

- 0.3.1 - 24/02/2024
  - No `v` in the version tag

- 0.3.0 - 24/02/2024
  - Filter arguments to create the key
  - Properly type the decorator
  - Fix the workflow using Poetry

- 0.2.0 - 21/02/2024
  - Move to Poetry

- 0.1.2 - 24/03/2021
  - Improve keys in the Redis database

- 0.1.1 - 24/03/2021
  - Make sure we do not wait forever
  - Improve stats
  - Improve keys in the Redis database

- 0.1.0 - 16/03/2021
  - First usable version
