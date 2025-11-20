# backend/main.py

import os
import json
import time
import hashlib
import tempfile
import subprocess
import logging
import re

from typing import Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# internal services
from backend.services.fairness import run_fairness_audit
from backend.services.explain import generate_explanation
from backend.services.sui_client import anchor_audit_on_sui

load_dotenv()
logger = logging.getLogger(__name__)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))

app = FastAPI(
    title="The Pursuit of Fairness - Backend",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TMP_DIR = os.path.join(os.getcwd(), "tmp")
os.makedirs(TMP_DIR, exist_ok=True)


# -------------------------------------------------------------------
# TEMP FILE HANDLING
# -------------------------------------------------------------------

def save_temp_upload(upload_file: UploadFile, max_mb=MAX_UPLOAD_MB) -> str:
    """Save uploaded CSV safely to /tmp."""
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


# -------------------------------------------------------------------
# WALRUS UPLOAD via NODE.JS uploader (THE ONLY VALID IMPLEMENTATION)
# -------------------------------------------------------------------

def upload_bundle_to_walrus(bundle_path: str) -> Dict[str, Any]:
    """
    Calls Node uploader:
      node backend/walrus-uploader/upload.js <bundle_path>

    Expects JSON output like:
    {
       "blobId": "...",
       "objectId": "...",
       "walrusURL": "...",
       "objectURL": "...",
       "raw": "..."
    }
    """

    try:
        result = subprocess.run(
            ["node", "backend/walrus-uploader/upload.js", bundle_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        stdout = result.stdout
        stderr = result.stderr

        if result.returncode != 0:
            raise RuntimeError(f"Walrus uploader failed:\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}")

        # Extract JSON block from stdout
        json_block = None
        for line in stdout.splitlines():
            if line.strip().startswith("{") and line.strip().endswith("}"):
                json_block = line.strip()
                break

        if not json_block:
            raise RuntimeError(f"Walrus uploader produced no JSON.\nOutput was:\n{stdout}")

        walrus_info = json.loads(json_block)

        logger.info("Walrus upload success: blob=%s object=%s",
                    walrus_info.get("blobId"),
                    walrus_info.get("objectId")
        )

        return walrus_info

    except Exception as e:
        raise RuntimeError(f"Walrus upload error: {e}")


# -------------------------------------------------------------------
# MAIN ENDPOINT
# -------------------------------------------------------------------

@app.post("/upload-dataset")
async def upload_dataset(background: BackgroundTasks, file: UploadFile = File(...)):
    logger.info("File received: %s", file.filename)

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")

    # 1. Save CSV
    try:
        csv_path = save_temp_upload(file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 2. Load DataFrame
    import pandas as pd
    try:
        df = pd.read_csv(csv_path)
    except Exception:
        background.add_task(remove_file_safe, csv_path)
        raise HTTPException(status_code=400, detail="Invalid CSV file.")

    # 3. Fairness metrics
    try:
        metrics = run_fairness_audit(df)
    except Exception as e:
        logger.exception("Fairness error")
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

    # 5. Build bundle JSON
    bundle = {
        "timestamp": int(time.time()),
        "filename": file.filename,
        "rows": int(df.shape[0]),
        "columns": list(df.columns),
        "metrics": metrics,
        "explanation": explanation,
        "version": "1.0.0"
    }

    # 6. Write bundle.json
    bundle_path = os.path.join(TMP_DIR, f"bundle_{int(time.time())}.json")
    with open(bundle_path, "w") as f:
        json.dump(bundle, f, indent=2)

    # 7. Upload to Walrus via Node.js
    try:
        walrus_info = upload_bundle_to_walrus(bundle_path)
    except Exception as e:
        logger.exception("Walrus upload failed")
        background.add_task(remove_file_safe, csv_path)
        background.add_task(remove_file_safe, bundle_path)
        return JSONResponse(status_code=500, content={
            "status": "walrus_upload_failed",
            "error": str(e),
            "bundle": bundle
        })

    blob_id = walrus_info.get("blobId")
    object_id = walrus_info.get("objectId")

    # 8. Anchor on Sui
    try:
        fairness_score = metrics.get("fairness_score") if isinstance(metrics, dict) else None
        sui_result = anchor_audit_on_sui(blob_id, fairness_score)
    except Exception as e:
        logger.exception("Sui anchoring failed")
        sui_result = {"error": str(e)}

    # 9. Cleanup
    background.add_task(remove_file_safe, csv_path)
    background.add_task(remove_file_safe, bundle_path)

    # 10. Return result
    # Ensure proof.blob_hash reflects the real walrus blob id when possible
    try:
        if isinstance(sui_result, dict):
            proof = sui_result.get("proof")
            if proof is None:
                proof = {}
                sui_result["proof"] = proof

            # prefer original blobId or normalized blob id
            real_blob = walrus_info.get("blobId") or walrus_info.get("blob_id") or blob_id
            if real_blob and not proof.get("blob_hash"):
                proof["blob_hash"] = real_blob
            if "fairness_score" not in proof and isinstance(metrics, dict) and metrics.get("fairness_score") is not None:
                proof["fairness_score"] = metrics.get("fairness_score")
            if "timestamp" not in proof:
                proof["timestamp"] = int(time.time())
            if "proof_hash" not in proof and sui_result.get("proof_hash"):
                proof["proof_hash"] = sui_result.get("proof_hash")
    except Exception:
        # don't fail response if augmentation fails
        pass

    return {
        "status": "success",
        "bundle": bundle,
        "walrus": walrus_info,
        "sui": sui_result
    }


@app.get("/")
def root():
    return {"message": "Backend running"}
