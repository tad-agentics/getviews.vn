FROM python:3.12-slim

# ffmpeg: frame extraction for R2 upload (corpus ingest pipeline)
# libpango-1.0-0 + libcairo2 + libpangoft2-1.0-0: WeasyPrint renderer
# for D.1.1 `/script/drafts/:id/export?format=pdf`. Shared libs only;
# the Python wheel handles the bindings.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
COPY getviews_pipeline/ ./getviews_pipeline/
RUN pip install --no-cache-dir -e ".[logs]"

COPY main.py .
COPY scripts/ ./scripts/

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", \
     "--timeout-keep-alive", "75", "--limit-concurrency", "20"]
