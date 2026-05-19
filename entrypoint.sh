#!/bin/sh
set -e

if [ ! -f "$DB_PATH" ] && [ ! -f "puns.db" ]; then
    echo "No database found — running init_db.py"
    python init_db.py
fi

exec python server.py
