#!/bin/sh
# ============================================================
#  Create the test database on first boot of postgres_dev.
# ------------------------------------------------------------
#  Runs automatically from /docker-entrypoint-initdb.d — but ONLY
#  when the data volume is empty (i.e. after `docker compose down -v`
#  or `docker volume rm postgres_dev_data`).
#
#  Reads TEST_POSTGRES_DB from the container env (see docker-compose.yml),
#  defaulting to `test_blog_db` if unset.
# ============================================================
set -e

TEST_DB="${TEST_POSTGRES_DB:-test_blog_db}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE "$TEST_DB" OWNER "$POSTGRES_USER";
EOSQL
