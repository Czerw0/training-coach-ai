FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# uv as the installer (pinned binary, no system packages needed). No apt-get:
# every dependency ships a manylinux wheel (psycopg2-binary bundles libpq), and
# --no-build makes the install fail loudly instead of silently needing gcc.
COPY --from=ghcr.io/astral-sh/uv:0.8.4 /uv /usr/local/bin/uv

# Install Python dependencies first (layer caching — only rebuilds if requirements change)
COPY requirements.txt .
RUN uv pip install --system --no-cache --no-build -r requirements.txt

# Copy the rest of the application code
COPY . .

# Collect static files for whitenoise at build time — settings need these vars
# to import, but collectstatic never touches the DB, so dummies are enough
RUN SECRET_KEY=build-only DATABASE_URL=sqlite:////tmp/build.sqlite3 \
    python manage.py collectstatic --noinput

# Expose the port gunicorn will run on
EXPOSE 8000

# Run migrations and gunicorn at startup
CMD python manage.py migrate --noinput && \
    gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 1 --timeout 300
