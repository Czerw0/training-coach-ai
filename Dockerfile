FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# no apt-get: every dependency ships a wheel; --no-build fails loudly if one doesn't
COPY --from=ghcr.io/astral-sh/uv:0.8.4 /uv /usr/local/bin/uv

# dependencies before code, so the layer stays cached until requirements change
COPY requirements.txt .
RUN uv pip install --system --no-cache --no-build -r requirements.txt

COPY . .

# dummy vars: settings need them to import, collectstatic never touches the DB
RUN SECRET_KEY=build-only DATABASE_URL=sqlite:////tmp/build.sqlite3 \
    python manage.py collectstatic --noinput

EXPOSE 8000

CMD python manage.py migrate --noinput && \
    gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 1 --timeout 300
