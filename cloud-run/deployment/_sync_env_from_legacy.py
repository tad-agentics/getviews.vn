#!/usr/bin/env python3
"""Read split Cloud Run env → write gv-user.env and gv-batch.env (gitignored).

Legacy single service ``getviews-pipeline`` is retired; this script pulls
``getviews-pipeline-user`` and ``getviews-pipeline-batch`` separately and
ensures the user file includes ``BATCH_SERVICE_BASE_URL`` when missing.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = "project-ddfb2960-ee81-4c98-b4f"
REGION = "asia-southeast1"
DEPLOYMENT_DIR = Path(__file__).resolve().parent


def gcloud_json(service: str) -> dict:
    out = subprocess.check_output(
        [
            "gcloud",
            "run",
            "services",
            "describe",
            service,
            f"--project={ROOT}",
            f"--region={REGION}",
            "--format=json",
        ],
        text=True,
    )
    return json.loads(out)


def gcloud_url(service: str) -> str:
    return subprocess.check_output(
        [
            "gcloud",
            "run",
            "services",
            "describe",
            service,
            f"--project={ROOT}",
            f"--region={REGION}",
            "--format=value(status.url)",
        ],
        text=True,
    ).strip()


def env_from_desc(d: dict) -> dict[str, str]:
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
            raise SystemExit(1)
    return raw


def write_env_file(path: str, env: dict[str, str], *, header: str) -> None:
    lines = [f"# {header} — {path.rsplit('/', 1)[-1]}"]
    for k in sorted(env.keys()):
        v = env[k]
        if v is None or v == "":
            continue
        v = v.replace("\r", " ").replace("\n", " ")
        if any(c in v for c in " \n\t#='\"") or v != v.strip():
            v = v.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{k}="{v}"')
        else:
            lines.append(f"{k}={v}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> int:
    d_user = gcloud_json("getviews-pipeline-user")
    d_batch = gcloud_json("getviews-pipeline-batch")

    u = env_from_desc(d_user)
    b = env_from_desc(d_batch)

    batch_url = gcloud_url("getviews-pipeline-batch").rstrip("/")
    if not u.get("BATCH_SERVICE_BASE_URL"):
        u["BATCH_SERVICE_BASE_URL"] = batch_url

    u["SERVICE_ROLE"] = "user"
    b["SERVICE_ROLE"] = "batch"

    if "R2_BUCKET" in u and "R2_BUCKET_NAME" not in u:
        u["R2_BUCKET_NAME"] = u["R2_BUCKET"]
    if "R2_BUCKET" in b and "R2_BUCKET_NAME" not in b:
        b["R2_BUCKET_NAME"] = b["R2_BUCKET"]

    out_u = str(DEPLOYMENT_DIR / "gv-user.env")
    out_b = str(DEPLOYMENT_DIR / "gv-batch.env")
    write_env_file(out_u, u, header="from gcloud describe getviews-pipeline-user")
    write_env_file(out_b, b, header="from gcloud describe getviews-pipeline-batch")
    print("wrote", out_u, "keys", len(u))
    print("wrote", out_b, "keys", len(b))
    print("BATCH_SERVICE_BASE_URL", u.get("BATCH_SERVICE_BASE_URL", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
