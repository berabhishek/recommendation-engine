FROM python:3.10-slim

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

RUN pip install --upgrade pip \
    && pip install .

RUN python scripts/create_db_template.py

EXPOSE 3000

ENTRYPOINT ["python", "-m", "scripts.docker_entrypoint"]
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3000"]
