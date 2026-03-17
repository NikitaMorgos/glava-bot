"""Дашборд разработчика — /dev/."""
import json
import os
import subprocess
from datetime import datetime

import psycopg2
import requests
from flask import Blueprint, render_template, request, jsonify, session

from admin.auth import role_required

bp = Blueprint("dev", __name__, url_prefix="/dev")


def _run(cmd: list[str], timeout: int = 5) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (result.stdout + result.stderr).strip()
    except Exception as e:
        return f"ERROR: {e}"


def _service_status(name: str) -> dict:
    out = _run(["systemctl", "is-active", name])
    active = out.strip() == "active"
    uptime_out = _run(["systemctl", "show", name, "--property=ActiveEnterTimestamp"])
    ts_str = uptime_out.replace("ActiveEnterTimestamp=", "").strip()
    return {"name": name, "active": active, "since": ts_str}


def _db_metrics() -> dict:
    try:
        db_url = os.environ.get("DATABASE_URL", "")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        metrics = {}
        for table in ("users", "voices", "photos", "drafts"):
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                metrics[table] = cur.fetchone()[0]
            except Exception:
                metrics[table] = "—"
        cur.close()
        conn.close()
        return metrics
    except Exception as e:
        return {"error": str(e)}


def _s3_metrics() -> dict:
    try:
        import boto3
        s3 = boto3.client(
            "s3",
            endpoint_url=os.environ.get("S3_ENDPOINT_URL"),
            aws_access_key_id=os.environ.get("S3_ACCESS_KEY"),
            aws_secret_access_key=os.environ.get("S3_SECRET_KEY"),
            region_name=os.environ.get("S3_REGION", "ru-central1"),
        )
        bucket = os.environ.get("S3_BUCKET_NAME", "")
        paginator = s3.get_paginator("list_objects_v2")
        count, total_size = 0, 0
        for page in paginator.paginate(Bucket=bucket):
            for obj in page.get("Contents", []):
                count += 1
                total_size += obj["Size"]
        return {"count": count, "size_mb": round(total_size / 1024 / 1024, 1)}
    except Exception as e:
        return {"error": str(e)}


def _error_log() -> list[str]:
    out = _run([
        "journalctl", "-u", "glava", "-u", "glava-cabinet",
        "-p", "err", "-n", "30", "--no-pager", "--output=short"
    ])
    return out.splitlines() if out else []


def _git_info() -> dict:
    commit = _run(["git", "-C", "/opt/glava", "log", "-1", "--format=%h|%s|%ci"])
    if "|" in commit:
        parts = commit.split("|", 2)
        return {"hash": parts[0], "message": parts[1], "date": parts[2]}
    return {"hash": "—", "message": commit, "date": "—"}


def _n8n_status() -> bool:
    try:
        r = requests.get("http://localhost:5678/healthz", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def _config_check() -> list[dict]:
    keys = [
        "BOT_TOKEN", "DATABASE_URL", "S3_ENDPOINT_URL", "S3_ACCESS_KEY",
        "S3_BUCKET_NAME", "OPENAI_API_KEY", "ASSEMBLYAI_API_KEY",
        "MYMEET_API_KEY", "YOOKASSA_SHOP_ID", "YOOKASSA_SECRET_KEY",
        "ADMIN_SECRET_KEY", "ADMIN_PASSWORD_DEV", "ADMIN_PASSWORD_DASHA", "ADMIN_PASSWORD_LENA",
    ]
    return [{"key": k, "set": bool(os.environ.get(k))} for k in keys]


# ─────────────────────────────────────────────────────────────────
@bp.route("/")
@role_required("dev", "dasha", "lena")
def dashboard():
    services = [
        _service_status("glava"),
        _service_status("glava-cabinet"),
        _service_status("glava-admin"),
    ]
    db_metrics = _db_metrics()
    s3_metrics = _s3_metrics()
    errors = _error_log()
    git = _git_info()
    n8n_ok = _n8n_status()
    config = _config_check()

    return render_template(
        "dev/dashboard.html",
        services=services,
        db_metrics=db_metrics,
        s3_metrics=s3_metrics,
        errors=errors,
        git=git,
        n8n_ok=n8n_ok,
        config=config,
        now=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    )


@bp.route("/restart/<service>", methods=["POST"])
@role_required("dev")
def restart_service(service: str):
    allowed = {"glava", "glava-cabinet", "glava-admin", "glava-n8n"}
    if service not in allowed:
        return jsonify({"ok": False, "error": "not allowed"}), 403
    if service == "glava-n8n":
        out = _run(["docker", "restart", "glava-n8n"], timeout=30)
    else:
        out = _run(["systemctl", "restart", service], timeout=30)
    return jsonify({"ok": True, "output": out})
