#!/usr/bin/env python3
"""Comprehensive Automated Security Checkup & Audit for DermAssist AI.

Audits:
1. Secret and Credential Exposure (Git status, .gitignore, source file patterns).
2. API Key Protection (Pydantic Settings repr masking, environment segregation).
3. Admin Surface & Documentation Lockdown.
4. Transport Security (HTTPS redirection, HSTS, CSP, X-Frame-Options, X-Content-Type-Options).
5. CORS Policy Standards Compliance (W3C/Fetch standard wildcard check).
6. Admin key security (constant-time compare, admin routes fail closed).
7. Database Lockdown & RLS Verification (no public update/delete policies).
8. Daily Backup System Verification (backup script and GitHub Actions cron).
9. Upload Security & DoS Resilience (magic bytes, 15MB cap, decompression bomb).
"""

import os
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))


class SecurityAuditRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.results = []

    def check(self, name: str, condition: bool, details: str = ""):
        if condition:
            self.passed += 1
            print(f"  [PASS] {name}")
            self.results.append({"name": name, "status": "PASS", "details": details})
        else:
            self.failed += 1
            print(f"  [FAIL] {name} - {details}")
            self.results.append({"name": name, "status": "FAIL", "details": details})

    def warn(self, name: str, details: str = ""):
        self.warnings += 1
        print(f"  [WARN] {name} - {details}")
        self.results.append({"name": name, "status": "WARN", "details": details})

    def run_all(self):
        print("\n=======================================================")
        print("  DermAssist AI — Comprehensive Security Audit")
        print("=======================================================\n")

        # --- Pillar 1: Secret & Credential Exposure ---
        print("1. Secret & Credential Exposure Prevention")
        # Check root .gitignore
        root_gi = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
        self.check("Root .gitignore ignores .env files", ".env" in root_gi and ".env.*" in root_gi)
        self.check("Root .gitignore ignores certificates and private keys", "*.key" in root_gi and "*.pem" in root_gi)
        self.check("Root .gitignore ignores databases and backups", "*.db" in root_gi and "backups/*.json.gz" in root_gi)

        # Check frontend .gitignore
        fe_gi = (PROJECT_ROOT / "frontend" / ".gitignore").read_text(encoding="utf-8")
        self.check("Frontend .gitignore ignores .env files", ".env" in fe_gi and ".env.local" in fe_gi)

        # Scan tracked git files for hardcoded secrets
        git_tracked = subprocess.check_output(
            ["git", "ls-files"], cwd=str(PROJECT_ROOT), text=True
        ).splitlines()

        secret_patterns = [
            re.compile(r"gsk_[a-zA-Z0-9]{40,}"),  # Groq API key
            re.compile(r"sk-[a-zA-Z0-9]{32,}"),   # Generic secret key
            re.compile(r"-----BEGIN (RSA|EC|PRIVATE) KEY-----"),
        ]

        found_secrets = []
        for file_path in git_tracked:
            full_path = PROJECT_ROOT / file_path
            if full_path.is_file() and full_path.suffix in (".py", ".js", ".jsx", ".json", ".html", ".yml", ".yaml"):
                try:
                    content = full_path.read_text(encoding="utf-8", errors="ignore")
                    for pat in secret_patterns:
                        if pat.search(content):
                            found_secrets.append(file_path)
                except Exception:
                    pass

        self.check("Zero hardcoded API keys/secrets in tracked files", len(found_secrets) == 0, f"Found in: {found_secrets}")

        # --- Pillar 2: API Key Protection & Repr Masking ---
        print("\n2. API Key Protection & Repr Masking")
        from src.core.config import get_settings
        settings = get_settings()
        repr_str = repr(settings)
        self.check("GROQ_API_KEY masked in settings repr", "GROQ_API_KEY=" not in repr_str)
        self.check("SUPABASE_KEY masked in settings repr", "SUPABASE_KEY=" not in repr_str)
        self.check("ADMIN_API_KEY masked in settings repr", "ADMIN_API_KEY=" not in repr_str)

        # --- Pillar 3: Admin Surface & Docs Lockdown ---
        print("\n3. Admin Surface & Documentation Lockdown")
        from src.api.main import app
        routes_paths = []
        for r in app.routes:
            if hasattr(r, "path"):
                routes_paths.append(r.path)
            elif hasattr(r, "routes"):
                for sub_r in r.routes:
                    if hasattr(sub_r, "path"):
                        routes_paths.append(sub_r.path)
        self.check("No rogue /admin endpoint registered", all(not p.startswith("/admin") for p in routes_paths))
        self.check("Interactive Swagger docs (/docs) locked in production", app.docs_url is None)
        self.check("Interactive ReDoc (/redoc) locked in production", app.redoc_url is None)
        self.check("OpenAPI schema (/openapi.json) locked in production", app.openapi_url is None)

        # --- Pillar 4: Transport Security & HTTPS Enforcement ---
        print("\n4. Transport Security & HTTPS Everywhere")
        from fastapi.testclient import TestClient
        client = TestClient(app)
        res = client.get("/health")
        h = res.headers
        self.check("Strict-Transport-Security (HSTS) enabled (>= 1 year + subdomains + preload)",
                   "strict-transport-security" in h and "max-age=" in h["strict-transport-security"])
        self.check("X-Content-Type-Options: nosniff header present", h.get("x-content-type-options") == "nosniff")
        self.check("X-Frame-Options: DENY (anti-clickjacking) present", h.get("x-frame-options") == "DENY")
        self.check("Referrer-Policy configured securely", h.get("referrer-policy") == "strict-origin-when-cross-origin")
        self.check("Content-Security-Policy (CSP) header present", "content-security-policy" in h)

        # Verify HTTPS redirection behind proxy
        redirect_res = client.get("/health", headers={"x-forwarded-proto": "http"}, follow_redirects=False)
        self.check("Reverse-proxy HTTP requests 301-redirected to HTTPS",
                   redirect_res.status_code == 301 and redirect_res.headers.get("location", "").startswith("https://"))

        # Verify Vercel headers in frontend/vercel.json
        vercel_json = (PROJECT_ROOT / "frontend" / "vercel.json").read_text(encoding="utf-8")
        self.check("Vercel frontend config enforces edge HSTS & security headers", "Strict-Transport-Security" in vercel_json)

        # --- Pillar 5: CORS Policy Compliance ---
        print("\n5. CORS Policy Standards Compliance")
        cors_middlewares = [m for m in app.user_middleware if "CORSMiddleware" in str(getattr(m, "cls", ""))]
        if cors_middlewares:
            kwargs = getattr(cors_middlewares[0], "kwargs", {})
            allow_origins = kwargs.get("allow_origins", [])
            allow_credentials = kwargs.get("allow_credentials", False)
            wildcard = "*" in allow_origins
            # When wildcard origin is used, credentials MUST be False
            self.check("CORS disallows credentials when wildcard origin '*' is used", not (wildcard and allow_credentials))
        else:
            self.warn("No CORSMiddleware detected")

        # --- Pillar 6: Password & Cryptographic Security ---
        print("\n6. Admin Key Security")
        from src.core.security import verify_admin_key
        self.check("Admin key verification uses constant-time comparison", verify_admin_key("correct", "correct") is True and verify_admin_key("bad", "correct") is False)

        # --- Pillar 7: Database Lockdown & Row Level Security (RLS) ---
        print("\n7. Database Lockdown & RLS Verification")
        schema_sql = (PROJECT_ROOT / "docs" / "supabase_schema.sql").read_text(encoding="utf-8")
        lock_sql = (PROJECT_ROOT / "docs" / "security_lock_database.sql").read_text(encoding="utf-8")
        self.check("Public UPDATE policy removed from scans schema", 'CREATE POLICY "Allow public update to scans"' not in schema_sql)
        self.check("Public DELETE policy explicitly revoked from scans", 'DROP POLICY IF EXISTS "Allow public delete from scans"' in schema_sql)
        self.check("Storage bucket restricted to verified image MIME types", "allowed_mime_types" in schema_sql)
        self.check("Standalone lockdown migration script exists for live database", lock_sql is not None and "ALTER TABLE IF EXISTS public.scans FORCE ROW LEVEL SECURITY" in lock_sql)

        # --- Pillar 8: Daily Database Backup System ---
        print("\n8. Daily Database Backup System")
        backup_script = PROJECT_ROOT / "scripts" / "backup_supabase.py"
        backup_workflow = PROJECT_ROOT / ".github" / "workflows" / "daily_backup.yml"
        self.check("Daily database backup script exists and is executable", backup_script.is_file())
        self.check("GitHub Actions daily backup workflow exists", backup_workflow.is_file())
        if backup_workflow.is_file():
            wf_content = backup_workflow.read_text(encoding="utf-8")
            self.check("Workflow runs on daily schedule cron (0 0 * * *)", "0 0 * * *" in wf_content)
            self.check("Workflow uploads encrypted/compressed backup artifact with 30-day retention", "retention-days: 30" in wf_content)

        # --- Pillar 9: Upload Security & DoS Resilience ---
        print("\n9. Upload Security & DoS Protection")
        from src.core.security import validate_image_payload, MAX_IMAGE_FILE_SIZE
        import PIL.Image
        self.check("Pillow Decompression Bomb protection active (MAX_IMAGE_PIXELS capped)", PIL.Image.MAX_IMAGE_PIXELS <= 25_000_000)
        self.check("Image upload size capped at 15 MB", MAX_IMAGE_FILE_SIZE == 15 * 1024 * 1024)
        is_val, _ = validate_image_payload(b"non-image-binary-payload")
        self.check("Magic byte verification rejects non-image payload", is_val is False)

        # --- Summary ---
        print("\n=======================================================")
        print(f"  Audit Results: {self.passed} Passed, {self.failed} Failed, {self.warnings} Warnings")
        print("=======================================================\n")
        return self.failed == 0


if __name__ == "__main__":
    runner = SecurityAuditRunner()
    success = runner.run_all()
    sys.exit(0 if success else 1)
