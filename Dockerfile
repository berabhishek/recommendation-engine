FROM python:3.14-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATABASE_URL=sqlite:////data/recommendation.db \
    DATA_DIR=/data/imdb-data \
    DB_TEMPLATE_PATH=/opt/db-template/recommendation.db \
    DB_INIT_MARKER=/data/.initialized

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app
COPY scripts ./scripts
COPY tests/fixtures/imdb-test/ /opt/test-data/imdb-test/

RUN pip install --upgrade pip \
    && pip install .

RUN python scripts/create_db_template.py

EXPOSE 3000

ENTRYPOINT ["python", "-m", "scripts.docker_entrypoint"]
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3000"]
