FROM python:3.12-slim

# ffmpeg: frame extraction for R2 upload (corpus ingest pipeline)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY cloud-run/pyproject.toml .
COPY cloud-run/getviews_pipeline/ ./getviews_pipeline/
RUN pip install --no-cache-dir -e ".[logs]"

COPY cloud-run/main.py .
COPY cloud-run/scripts/ ./scripts/

# HI-11 junction lookup reads PR1/PR6/HI-16 seed SQL at runtime (junction_content_class.py).
COPY supabase/migrations/20260510000004_two_axis_niche_pr1_schema.sql \
  supabase/migrations/20260510000004_two_axis_niche_pr1_schema.sql
COPY supabase/migrations/20260516190000_hi16_carousel_format_axis_junction.sql \
  supabase/migrations/20260516190000_hi16_carousel_format_axis_junction.sql
COPY supabase/migrations/20260630000003_creator_niches_16_music_real_estate.sql \
  supabase/migrations/20260630000003_creator_niches_16_music_real_estate.sql

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", \
     "--timeout-keep-alive", "75", "--limit-concurrency", "20"]
