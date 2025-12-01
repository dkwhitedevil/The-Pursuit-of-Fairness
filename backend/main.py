# backend/main.py
import os
import json
import time
import subprocess
import logging
import base64
import tempfile
from typing import Dict, Any, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Internal services
from services.sui_reader import read_audit_table
from services.fairness import run_fairness_audit
from services.explain import generate_explanation
from services.seal_node_bridge import seal_encrypt_node, prepare_identity
from services.walrus_client import WalrusClient

# Initialize
load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))

app = FastAPI(title="The Pursuit of Fairness", version="1.0.0", max_request_size=100*1024*1024)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TMP_DIR = os.path.join(os.getcwd(), "tmp")
os.makedirs(TMP_DIR, exist_ok=True)

# Walrus client instance (uses services/walrus_client.py)
walrus_client = WalrusClient()


# ---------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------
def run_command(cmd: list, timeout: int = 10) -> Dict[str, Any]:
    """
    Run a command and return stdout/stderr and the returncode.
    Non-raising; errors are returned in the dict.
    """
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        return {"cmd": cmd, "returncode": proc.returncode, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()}
    except subprocess.TimeoutExpired as e:
        return {"cmd": cmd, "error": "timeout", "timeout": timeout, "stdout": getattr(e, "stdout", ""), "stderr": getattr(e, "stderr", "")}
    except Exception as e:
        return {"cmd": cmd, "error": str(e)}


def save_temp_upload(upload_file: UploadFile, max_mb=MAX_UPLOAD_MB) -> str:
    filename = upload_file.filename or "upload.csv"
    safe_name = f"{int(time.time())}_{filename.replace(' ', '_')}"
    dest = os.path.join(TMP_DIR, safe_name)

    total = 0
    with open(dest, "wb") as f:
        while True:
            chunk = upload_file.file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_mb * 1024 * 1024:
                f.close()
                os.remove(dest)
                raise HTTPException(status_code=413, detail="File too large")
            f.write(chunk)

    return dest


def remove_file_safe(path: str):
    try:
        os.remove(path)
    except Exception:
        pass


# ---------------------------------------------------------------
# Walrus Upload helper
# ---------------------------------------------------------------
def upload_bundle_to_walrus(bundle_path: str) -> Dict[str, Any]:
    """
    Uploads encrypted bundle file using WalrusClient() (services.walrus_client.WalrusClient).
    Returns a dict with blobId/objectId/walrusURL/objectURL or raises RuntimeError.
    """
    try:
        with open(bundle_path, "rb") as f:
            data = f.read()

        result = walrus_client.upload_blob(data, filename=os.path.basename(bundle_path))
        # validate expected keys
        if not isinstance(result, dict) or "blobId" not in result:
            raise RuntimeError(f"Unexpected upload result: {result}")
        return result
    except Exception as e:
        raise RuntimeError(f"Walrus upload failed: {str(e)}")


# ---------------------------------------------------------------
# API — Main Pipeline (endpoints)
# ---------------------------------------------------------------
@app.get("/audit/proofs")
def get_all_proofs():
    try:
        proofs = read_audit_table()
        return {"status": "success", "count": len(proofs), "proofs": proofs}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/test-fairness")
async def test_fairness(file: UploadFile = File(...)):
    import pandas as pd
    df = pd.read_csv(file.file)
    metrics = run_fairness_audit(df)
    return metrics


@app.post("/debug-seal-encrypt")
async def debug_seal_encrypt(file: UploadFile = File(...)):
    """
    Test Seal encryption using a sample CSV file.
    Does NOT upload to Walrus or Sui.
    Just checks if seal_encrypt_node works.
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files allowed.")

    tmp_path = os.path.join(TMP_DIR, f"seal_test_{int(time.time())}.csv")

    try:
        with open(tmp_path, "wb") as f:
            f.write(await file.read())

        identity = prepare_identity()
        enc_identity, encrypted_b64, backup_key = seal_encrypt_node(tmp_path, identity)

        return {
            "status": "success",
            "identity": enc_identity,
            "encrypted_preview": encrypted_b64[:80] + "...",
            "backup_key_preview": backup_key[:80] + "...",
            "length_encrypted_b64": len(encrypted_b64),
            "length_backup_key_b64": len(backup_key),
        }

    except Exception as e:
        return {"status": "seal_error", "error": str(e)}

    finally:
        remove_file_safe(tmp_path)


@app.get("/debug-node")
def debug_node():
    return run_command(["node", "-v"])




@app.get("/debug-walrus-upload")
def debug_walrus_upload():
    """
    Upload a small static blob using the Python Walrus wrapper to ensure pipeline works.
    """
    try:
        sample_data = b"Hello Walrus! This is a debug test blob."
        result = walrus_client.upload_blob(sample_data, filename="debug.txt")

        return {
            "status": "success",
            "message": "Walrus upload working!",
            "blobId": result.get("blobId"),
            "objectId": result.get("objectId"),
            "walrusURL": result.get("walrusURL"),
            "objectURL": result.get("objectURL"),
            "raw": result,
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.get("/debug-sui")
def debug_sui():
    try:
        out = subprocess.check_output(["sui", "client", "active-address"], stderr=subprocess.STDOUT, text=True, timeout=8)
        return {"sui_output": out.strip()}
    except subprocess.CalledProcessError as e:
        return {"error": "sui command failed", "stdout": e.output, "stderr": str(e)}
    except Exception as e:
        return {"error": str(e)}

@app.get("/check/walrus")
def check_walrus():
    """
    Fully tests Walrus REST uploader on Render.
    Uploads a tiny blob: "Render Walrus Check".
    """
    try:
        test_data = b"Render Walrus Check"
        result = walrus_client.upload_blob(test_data, filename="render_test.txt")

        return {
            "status": "success",
            "message": "Walrus REST upload working on Render!",
            "blobId": result.get("blobId"),
            "objectId": result.get("objectId"),
            "walrusURL": result.get("walrusURL"),
            "objectURL": result.get("objectURL"),
            "raw": result
        }

    except Exception as e:
        return {
            "status": "failed",
            "error": str(e)
        }

    
# ---------------------------------------------------------
# DEBUG: Show important backend paths
# ---------------------------------------------------------
@app.get("/debug-paths")
def debug_paths():
    backend_root = os.getcwd()
    return {
        "cwd": backend_root,
        "expected_files": {
            "services/seal_client.js": os.path.exists(os.path.join(backend_root, "services", "seal_client.js")),
            "services/seal_node_bridge.py": os.path.exists(os.path.join(backend_root, "services", "seal_node_bridge.py")),
            "walrus-uploader/upload.js": os.path.exists(os.path.join(backend_root, "walrus-uploader", "upload.js")),
            "requirements.txt": os.path.exists(os.path.join(backend_root, "requirements.txt")),
            "main.py": os.path.exists(os.path.join(backend_root, "main.py")),
            "node_modules_root": os.path.exists(os.path.join(backend_root, "node_modules")),
            "node_modules_backend": os.path.exists(os.path.join(backend_root, "backend", "node_modules")),
            "walrus_client_exists": os.path.exists(os.path.join(backend_root, "services", "walrus_client.py")),
        }
    }

@app.get("/debug/anchor")
def debug_anchor(blob: str = "abcd1234", score: int = 50):
    return anchor_audit_js(blob, score, int(time.time()))

        
def anchor_audit_js(bundle_hash: str, fairness_score: int, timestamp: int) -> dict:
    """
    Calls the Node.js sui_anchor.js script to anchor audit data on Sui blockchain.
    """
    try:
        script_path = os.path.join(os.getcwd(), "services", "sui_anchor.js")

        # Pass arguments via environment variables
        env = os.environ.copy()
        env["BUNDLE_HASH"] = bundle_hash
        env["FAIRNESS_SCORE"] = str(fairness_score)
        env["TIMESTAMP"] = str(timestamp)

        result = subprocess.run(
            ["node", script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            timeout=40
        )

        if result.returncode != 0:
            return {
                "status": "error",
                "stderr": result.stderr.strip()
            }

        # Try parsing JSON output
        try:
            return json.loads(result.stdout)
        except:
            return {"status": "ok", "raw": result.stdout.strip()}

    except Exception as e:
        return {"status": "anchor_error", "error": str(e)}


# ---------------------------------------------------------------
# Upload dataset pipeline (existing)
# ---------------------------------------------------------------
@app.post("/upload-dataset")
async def upload_dataset(background: BackgroundTasks, file: UploadFile = File(...)):

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files allowed.")

    # 1. Save CSV
    csv_path = save_temp_upload(file)

    # 2. Load DataFrame
    import pandas as pd
    try:
        df = pd.read_csv(csv_path)
    except Exception:
        background.add_task(remove_file_safe, csv_path)
        raise HTTPException(status_code=400, detail="Invalid CSV")

    # 3. Fairness metrics
    try:
        metrics = run_fairness_audit(df)
    except Exception as e:
        metrics = {"error": str(e)}

    # 4. LLM explanation
    try:
        explanation = generate_explanation(metrics)
    except Exception:
        explanation = {
            "summary": "Explanation failed",
            "analysis": "",
            "recommendations": "",
            "confidence": "0"
        }

    # 5. Bundle JSON
    bundle = {
        "timestamp": int(time.time()),
        "filename": file.filename,
        "rows": int(df.shape[0]),
        "columns": list(df.columns),
        "metrics": metrics,
        "explanation": explanation,
        "version": "1.0.0"
    }
    bundle_bytes = json.dumps(bundle).encode("utf-8")

    # 6. Seal Encryption (Node)
    # 6. Seal Encryption (Node)
    try:
        audit_id = str(int(time.time()))   # UNIQUE AUDIT ID
        seal_identity = prepare_identity()

        temp_input = os.path.join(TMP_DIR, f"bundle_{audit_id}.json")
        with open(temp_input, "wb") as f:
            f.write(bundle_bytes)

        seal_identity, encrypted_b64, backup_key = seal_encrypt_node(temp_input, seal_identity)
        background.add_task(remove_file_safe, temp_input)

        encrypted_path = os.path.join(TMP_DIR, f"enc_{audit_id}.bin")
        with open(encrypted_path, "wb") as f:
            f.write(base64.b64decode(encrypted_b64))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Seal encryption failed: {e}")

    # 7. Upload to Walrus
    try:
        walrus_info = upload_bundle_to_walrus(encrypted_path)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "walrus_upload_failed", "error": str(e), "bundle": bundle}
        )

    # 8. Anchor on Sui
    try:
        fairness_score = metrics.get("fairness_score", 0)
        blob_id = walrus_info.get("blobId")
        if not blob_id:
            raise HTTPException(status_code=500, detail="Walrus upload succeeded but blobId is missing")
        sui_result = anchor_audit_js(blob_id,int(fairness_score),int(time.time()))
    except Exception as e:
        sui_result = {"error": str(e)}

    # Cleanup temp files
    background.add_task(remove_file_safe, csv_path)
    background.add_task(remove_file_safe, encrypted_path)

    return {
        "status": "success",
        "audit_id": audit_id,
        "encrypted_identity": seal_identity,
        "bundle_metadata": bundle,
        "walrus": walrus_info,
        "sui": sui_result,
        "backup_key": backup_key
    }


# ---------------------------------------------------------------
# NEW: Check endpoints for Sui / Walrus / Seal / Node / Env
# ---------------------------------------------------------------
@app.get("/check/all")
def check_all(run_seal_smoketest: bool = Query(False, description="If true, attempt a Seal encryption smoke test (can be slow)")):
    """
    Run a suite of quick checks: node, walrus_uploader, sui, seal (optional).
    Returns a JSON report summarizing command outputs and health flags.
    """
    report = {
        "node": run_command(["node", "-v"]),
        "npm": run_command(["npm", "-v"]),
        "walrus_uploader": run_command(["node", "walrus-uploader/upload.js"], timeout=5),
        "sui": run_command(["sui", "--version"]),
        "cwd": os.getcwd(),
    }

    if run_seal_smoketest:
        try:
            pid = prepare_identity()
            # make a tiny temp file
            with tempfile.NamedTemporaryFile("w+b", delete=False) as tmp:
                tmp.write(b"seal-smoke-test")
                tmp.flush()
                tmp_path = tmp.name

            try:
                sid, enc_b64, backup = seal_encrypt_node(tmp_path, pid)
                report["seal_smoke"] = {"ok": True, "audit_id": sid, "backup_key_present": bool(backup)}
            except Exception as e:
                report["seal_smoke"] = {"ok": False, "error": str(e)}
            finally:
                remove_file_safe(tmp_path)
        except Exception as e:
            report["seal_smoke"] = {"ok": False, "error": f"prepare_identity failed: {e}"}

    return report


@app.get("/check/node")
def check_node():
    return run_command(["node", "-v"])


@app.get("/check/npm")
def check_npm():
    return run_command(["npm", "-v"])

@app.get("/check/sui/active-address")
def check_sui_active_address():
    return run_command(["sui", "client", "active-address"])


@app.get("/check/sui/version")
def check_sui_version():
    return run_command(["sui", "--version"])


@app.post("/check/seal/smoke")
def check_seal_smoke_test():
    try:
        pid = prepare_identity()
    except Exception as e:
        return {"ok": False, "error": f"prepare_identity failed: {e}"}

    with tempfile.NamedTemporaryFile("w+b", delete=False) as tmp:
        tmp.write(b"seal-smoke-test")
        tmp.flush()
        tmp_path = tmp.name

    try:
        audit_id, encrypted_b64, backup_key = seal_encrypt_node(tmp_path, pid)
        return {"ok": True, "audit_id": audit_id, "backup_key_present": bool(backup_key)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        remove_file_safe(tmp_path)


@app.get("/check/env")
def check_env():
    env_keys = ["HOME", "USER", "PATH", "SUI_RPC_URL", "FRONTEND_URL"]
    env = {k: os.environ.get(k, None) for k in env_keys}
    return {"cwd": os.getcwd(), "env": env}


# ---------------------------------------------------------------
# Root
# ---------------------------------------------------------------
@app.get("/")
def root():
    return {"message": "Backend running"}
