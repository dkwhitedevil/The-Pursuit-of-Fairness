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
from services.sui_client import anchor_audit_on_sui
from services.seal_node_bridge import seal_encrypt_node, prepare_identity
from services.walrus_client import WalrusClient   # make sure this import exists

walrus_client = WalrusClient()
load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))

app = FastAPI(title="The Pursuit of Fairness - Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TMP_DIR = os.path.join(os.getcwd(), "tmp")
os.makedirs(TMP_DIR, exist_ok=True)


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
    Uses the JS uploader script at walrus-uploader/upload.js.
    Returns parsed JSON output (uploader prints JSON as last line) or raises RuntimeError.
    """
    try:
        result = subprocess.run(
            ["node", "walrus-uploader/upload.js", bundle_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Walrus uploader failed:\n{result.stdout}\n{result.stderr}"
            )

        try:
            # Walrus upload.js always prints JSON as final line
            data = json.loads(result.stdout.strip().split("\n")[-1])
            return data
        except Exception:
            raise RuntimeError(
                f"Walrus uploader did not output valid JSON:\n{result.stdout}\n{result.stderr}"
            )

    except Exception as e:
        raise RuntimeError(f"Walrus upload error: {e}")


# ---------------------------------------------------------------
# API — Main Pipeline (existing endpoints preserved)
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


@app.post("/debug-walrus-upload")
async def debug_walrus_upload(file: UploadFile = File(...)):
    """
    Test Walrus upload alone.
    No SEAL, no Sui — only upload to Walrus.
    """

    # Validate file
    if not file:
        raise HTTPException(status_code=400, detail="Upload a file")

    # Save temporarily
    import tempfile, os

    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(await file.read())
            tmp.flush()
            tmp_path = tmp.name

        # Upload to Walrus using Node uploader
        try:
            result = walrus_client.upload_blob(open(tmp_path, "rb").read(), filename=file.filename)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Walrus upload failed: {e}")

        return {
            "status": "success",
            "filename": file.filename,
            "walrus": result
        }

    finally:
        if "tmp_path" in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)
            
@app.post("/debug-seal-encrypt")
async def debug_seal_encrypt(file: UploadFile = File(...)):
    """
    Test Seal encryption using a sample CSV file.
    Does NOT upload to Walrus or Sui.
    Just checks if seal_encrypt_node works.
    """

    # 1. Validate CSV
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files allowed.")

    # 2. Save temporary CSV
    tmp_path = os.path.join(TMP_DIR, f"seal_test_{int(time.time())}.csv")

    try:
        with open(tmp_path, "wb") as f:
            f.write(await file.read())

        # 3. Run Seal Encryption
        identity = prepare_identity()
        enc_identity, encrypted_b64, backup_key = seal_encrypt_node(tmp_path, identity)

        # 4. Return output
        return {
            "status": "success",
            "identity": enc_identity,
            "encrypted_preview": encrypted_b64[:80] + "...",   # don't return full for safety
            "backup_key_preview": backup_key[:80] + "...",
            "length_encrypted_b64": len(encrypted_b64),
            "length_backup_key_b64": len(backup_key),
        }

    except Exception as e:
        return {
            "status": "seal_error",
            "error": str(e),
        }

    finally:
        # 5. Cleanup
        try:
            os.remove(tmp_path)
        except:
            pass

@app.get("/debug-node")
def debug_node():
    return run_command(["node", "-v"])


@app.get("/debug-walrus")
def debug_walrus():
    return run_command(["walrus", "--version"])


@app.get("/debug-sui")
def debug_sui():
    try:
        out = subprocess.check_output(["sui", "client", "active-address"], stderr=subprocess.STDOUT, text=True, timeout=8)
        return {"sui_output": out.strip()}
    except subprocess.CalledProcessError as e:
        return {"error": "sui command failed", "stdout": e.output, "stderr": str(e)}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------
# DEBUG: Show important backend paths
# ---------------------------------------------------------
@app.get("/debug-paths")
def debug_paths():
    import os

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
        }
    }


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
    try:
        audit_id = prepare_identity()

        temp_input = os.path.join(TMP_DIR, f"bundle_{audit_id}.json")
        with open(temp_input, "wb") as f:
            f.write(bundle_bytes)

        audit_id, encrypted_b64, backup_key = seal_encrypt_node(temp_input, audit_id)
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
        sui_result = anchor_audit_on_sui(walrus_info, fairness_score)
    except Exception as e:
        sui_result = {"error": str(e)}

    # Cleanup temp files
    background.add_task(remove_file_safe, csv_path)
    background.add_task(remove_file_safe, encrypted_path)

    return {
        "status": "success",
        "encrypted_identity": audit_id,
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
    Run a suite of quick checks: node, walrus, sui, seal (optional).
    Returns a JSON report summarizing command outputs and health flags.
    """
    report = {
        "node": run_command(["node", "-v"]),
        "npm": run_command(["npm", "-v"]),
        "walrus": run_command(["walrus", "--version"]),
        "sui": run_command(["sui", "--version"]),
        "cwd": os.getcwd(),
    }

    if run_seal_smoketest:
        # Attempt a lightweight Seal smoke test using the existing python bridge.
        # It will call prepare_identity() and then try to encrypt a tiny temp file.
        try:
            pid = prepare_identity()
            # make a tiny temp file
            with tempfile.NamedTemporaryFile("w+b", delete=False) as tmp:
                tmp.write(b"seal-smoke-test")
                tmp.flush()
                tmp_path = tmp.name

            try:
                sid, enc_b64, backup = seal_encrypt_node(tmp_path, pid)
                # on success remove temp
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


@app.get("/check/walrus/version")
def check_walrus_version():
    return run_command(["walrus", "--version"])


@app.post("/check/walrus/upload-test")
def check_walrus_upload_test(file_path: Optional[str] = Query(None, description="Path to a file inside container to upload (binary). If not provided, a small temp file is used.")):
    """
    Try running the walrus uploader script with a small test file.
    This DOES NOT delete anything from walrus; it simply attempts upload and returns uploader output.
    Provide a path that exists inside the container, or leave blank to use a generated temp file.
    """
    temp_created = False
    used_path = file_path
    if not file_path:
        # create a tiny temp file to upload
        fd, p = tempfile.mkstemp(prefix="walrus_test_", text=False)
        os.close(fd)
        with open(p, "wb") as f:
            f.write(b"walrus-upload-test")
        temp_created = True
        used_path = p

    try:
        cmd_result = run_command(["node", "walrus-uploader/upload.js", used_path], timeout=60)
        # return uploader stdout/stderr; caller is responsible for interpreting results
        return {"file_used": used_path, "result": cmd_result}
    finally:
        if temp_created:
            remove_file_safe(used_path)


@app.get("/check/sui/active-address")
def check_sui_active_address():
    return run_command(["sui", "client", "active-address"])


@app.get("/check/sui/version")
def check_sui_version():
    return run_command(["sui", "--version"])


@app.post("/check/seal/smoke")
def check_seal_smoke_test():
    """
    Explicit seal smoke test: will prepare identity and attempt to encrypt a tiny payload.
    Useful for verifying the Node bridge and installed JS deps are functional.
    """
    try:
        pid = prepare_identity()
    except Exception as e:
        return {"ok": False, "error": f"prepare_identity failed: {e}"}

    # tiny input
    with tempfile.NamedTemporaryFile("w+b", delete=False) as tmp:
        tmp.write(b"seal-smoke-test")
        tmp.flush()
        tmp_path = tmp.name

    try:
        audit_id, encrypted_b64, backup_key = seal_encrypt_node(tmp_path, pid)
        # do not keep the encrypted bytes on disk
        return {"ok": True, "audit_id": audit_id, "backup_key_present": bool(backup_key)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        remove_file_safe(tmp_path)


@app.get("/check/env")
def check_env():
    """
    Return a small summary of environment variables that are commonly needed.
    Avoid returning sensitive secrets.
    """
    env_keys = ["HOME", "USER", "PATH", "SUI_RPC_URL", "FRONTEND_URL"]
    env = {k: os.environ.get(k, None) for k in env_keys}
    return {"cwd": os.getcwd(), "env": env}


# ---------------------------------------------------------------
# Root
# ---------------------------------------------------------------
@app.get("/")
def root():
    return {"message": "Backend running"}
