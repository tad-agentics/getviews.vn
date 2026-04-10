FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY getviews_pipeline/ ./getviews_pipeline/
COPY main.py .

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", \
     "--timeout-keep-alive", "75", "--limit-concurrency", "20"]
