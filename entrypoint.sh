#!/bin/bash
set -o pipefail

echo "🔥 FORCING DEPLOYMENT TO WORK..."

wait_for_db() {
    echo "⏰ Waiting for database..."
    max_attempts=30
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if python manage.py check --database default > /dev/null 2>&1; then
            echo "✅ Database ready!"
            break
        else
            sleep 2
            attempt=$((attempt + 1))
        fi
        if [ $attempt -gt $max_attempts ]; then
            echo "❌ Database timeout"
            exit 1
        fi
    done
}

wait_for_db

if [ "$1" = "uvicorn" ]; then
    echo "🌐 Web server detected, running migrations..."
    python manage.py makemigrations || echo "✅ makemigrations done"
    python manage.py migrate --fake-initial || echo "✅ migrate --fake-initial done"
    python manage.py migrate --run-syncdb || echo "✅ migrate --run-syncdb done"
    python manage.py migrate || echo "✅ migrate done"
    python manage.py collectstatic --noinput || echo "✅ collectstatic done"
    echo "🚀 Starting web server..."
fi

exec "$@"