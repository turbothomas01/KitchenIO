FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    KITCHENIO_DB=/data/kitchenio.db

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY kitchenio ./kitchenio

RUN useradd --create-home --uid 10001 kitchenio && mkdir -p /data && chown -R kitchenio:kitchenio /data /app
USER kitchenio

EXPOSE 8000
VOLUME ["/data"]

CMD ["uvicorn", "kitchenio.app:app", "--host", "0.0.0.0", "--port", "8000"]
