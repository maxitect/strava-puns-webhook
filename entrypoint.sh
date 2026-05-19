#!/bin/sh
set -e

mkdir -p "$(dirname "${DB_PATH:-puns.db}")"

if [ ! -f "${DB_PATH:-puns.db}" ]; then
    echo "No database found — running init_db.py"
    python init_db.py
fi

exec python server.py
