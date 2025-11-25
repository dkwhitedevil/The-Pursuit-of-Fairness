# backend/main.py

import os
import json
import time
import subprocess
import logging
import base64

from typing import Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Internal services
from services.sui_reader import read_audit_table
from services.fairness import run_fairness_audit
from services.explain import generate_explanation
from services.sui_client import anchor_audit_on_sui
import uuid

# Correct Seal client (Node bridge)
from services.seal_node_bridge import seal_encrypt_node, prepare_identity

load_dotenv()
logger = logging.getLogger(__name__)

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
    except:
        pass


# ---------------------------------------------------------------
# Walrus Upload
# ---------------------------------------------------------------

def upload_bundle_to_walrus(bundle_path: str) -> Dict[str, Any]:
    try:
        result = subprocess.run(
            ["node", "backend/walrus-uploader/upload.js", bundle_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Walrus uploader failed:\n{result.stdout}\n{result.stderr}"
            )

        json_line = None
        for line in result.stdout.splitlines():
            if line.strip().startswith("{") and line.strip().endswith("}"):
                json_line = line
                break

        if not json_line:
            raise RuntimeError(f"No JSON output from Walrus uploader:\n{result.stdout}")

        return json.loads(json_line)

    except Exception as e:
        raise RuntimeError(f"Walrus upload error: {e}")


# ---------------------------------------------------------------
# API — Main Pipeline
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

@app.get("/debug-node")
def debug_node():
    import subprocess
    p = subprocess.Popen(
        ["node", "-v"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    out, err = p.communicate()
    return {"stdout": out.strip(), "stderr": err.strip()}

@app.get("/debug-walrus")
def debug_walrus():
    import subprocess
    p = subprocess.Popen(
        ["walrus", "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    out, err = p.communicate()
    return {"stdout": out.strip(), "stderr": err.strip()}


# ---------------------------------------------------------
# DEBUG: Check Sui CLI
# ---------------------------------------------------------
@app.get("/debug-sui")
def debug_sui():
    import subprocess
    p = subprocess.Popen(
        ["sui", "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    out, err = p.communicate()
    return {"stdout": out.strip(), "stderr": err.strip()}


# ---------------------------------------------------------
# DEBUG: Check Node installation
# ---------------------------------------------------------
@app.get("/debug-node")
def debug_node():
    import subprocess
    p = subprocess.Popen(
        ["node", "-v"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    out, err = p.communicate()
    return {"stdout": out.strip(), "stderr": err.strip()}


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
        }
    }

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
    except:
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
    except:
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
        fairness_score = metrics.get("fairness_score")
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


@app.get("/")
def root():
    return {"message": "Backend running"}
