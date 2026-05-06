# Cập nhật biến môi trường — `getviews-pipeline-user`

Dùng khi xoay key (Supabase, Gemini, EnsembleData) mà **không** build lại image.  
Chỉ thay placeholder; **không** dán secret vào chat/issue.

```bash
PROJECT_ID="$(gcloud config get-value project)"

gcloud run services update getviews-pipeline-user \
  --project "$PROJECT_ID" \
  --region asia-southeast1 \
  --update-env-vars "\
SERVICE_ROLE=user,\
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co,\
SUPABASE_ANON_KEY=YOUR_ANON_KEY,\
SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVICE_ROLE_KEY,\
SUPABASE_JWT_SECRET=YOUR_JWT_SECRET,\
GEMINI_API_KEY=YOUR_GEMINI_KEY,\
ENSEMBLE_DATA_API_KEY=YOUR_ENSEMBLE_KEY"
```

## Ghi chú

- **`--update-env-vars`**: chỉ ghi đè các key liệt kê; các biến khác trên service (proxy, R2, `BATCH_*`, …) giữ nguyên nếu không đưa vào chuỗi.
- **`SERVICE_ROLE=user`**: nên giữ để revision mới không ghi đè role pod (cùng image user/batch).
- **EnsembleData**: code đọc `ENSEMBLE_DATA_API_KEY` hoặc `ENSEMBLEDATA_API_KEY` / `ENSEMBLEDATA_API_TOKEN` — xem `getviews_pipeline/config.py`.
- **JWT**: có `SUPABASE_URL` thì JWKS mặc định derive; `SUPABASE_JWT_SECRET` chỉ khi bật fallback HS256.
- Giá trị có **dấu phẩy**: tránh đặt trong `--update-env-vars`; dùng Secret Manager + `--set-secrets` hoặc tách `gcloud run services update` theo từng nhóm.

Danh sách đầy đủ biến tùy chọn: `cloud-run/.env.example` và phần cuối `cloud-run/deploy.sh`.
