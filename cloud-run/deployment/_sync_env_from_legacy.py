#!/usr/bin/env python3
"""One-off: read getviews-pipeline env, write gv-user.env and gv-batch.env (gitignored)."""
import json
import subprocess
import sys

ROOT = "project-ddfb2960-ee81-4c98-b4f"
REGION = "asia-southeast1"


def gcloud_json(args: list[str]) -> dict:
    out = subprocess.check_output(
        ["gcloud", *args, f"--project={ROOT}", f"--region={REGION}", "--format=json"],
        text=True,
    )
    return json.loads(out)


def gcloud_value(args: list[str]) -> str:
    return subprocess.check_output(
        ["gcloud", *args, f"--project={ROOT}", f"--region={REGION}", "--format=value(status.url)"],
        text=True,
    ).strip()


def write_env_file(path: str, env: dict[str, str]) -> None:
    lines = [f"# generated from getviews-pipeline + split roles — {path.rsplit('/', 1)[-1]}"]
    for k in sorted(env.keys()):
        v = env[k]
        if v is None or v == "":
            continue
        # Cloud Run .env: avoid unescaped newlines
        v = v.replace("\r", " ").replace("\n", " ")
        if any(c in v for c in " \n\t#='\"") or v != v.strip():
            v = v.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{k}="{v}"')
        else:
            lines.append(f"{k}={v}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> int:
    d = gcloud_json(["run", "services", "describe", "getviews-pipeline"])
    c = d["spec"]["template"]["spec"]["containers"][0]
    raw: dict[str, str] = {}
    for e in c.get("env", []):
        n = e.get("name")
        v = e.get("value")
        if n and v is not None:
            raw[n] = v
        sk = (e.get("valueFrom") or {}).get("secretKeyRef")
        if n and sk:
            print("ERROR: secret ref not supported in this script:", n, file=sys.stderr)
            return 1

    for k in list(raw.keys()):
        if k == "SERVICE_ROLE":
            del raw[k]

    batch_url = gcloud_value(["run", "services", "describe", "getviews-pipeline-batch"]).rstrip("/")

    u = dict(raw)
    b = dict(raw)
    u["SERVICE_ROLE"] = "user"
    b["SERVICE_ROLE"] = "batch"
    u["BATCH_SERVICE_BASE_URL"] = batch_url

    if "R2_BUCKET" in u and "R2_BUCKET_NAME" not in u:
        u["R2_BUCKET_NAME"] = u["R2_BUCKET"]
    if "R2_BUCKET" in b and "R2_BUCKET_NAME" not in b:
        b["R2_BUCKET_NAME"] = b["R2_BUCKET"]

    base = "/Users/ductrinh/getviews.vn/getviews.vn-1/cloud-run/deployment"
    out_u = f"{base}/gv-user.env"
    out_b = f"{base}/gv-batch.env"
    write_env_file(out_u, u)
    write_env_file(out_b, b)
    print("wrote", out_u, "keys", len(u))
    print("wrote", out_b, "keys", len(b))
    print("BATCH_SERVICE_BASE_URL", batch_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
