import subprocess
import tempfile
import json
import os
from pathlib import Path
from typing import Dict, Any


NODE_UPLOADER = Path(__file__).parent.parent / "walrus-uploader" / "upload.js"


class WalrusClient:
    """Walrus client wrapper that invokes the Node uploader script and parses JSON output."""

    def upload_blob(self, bytes_data: bytes, filename: str = "bundle.json") -> Dict[str, Any]:
        tmp_path = None

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tf:
                tf.write(bytes_data)
                tf.flush()
                tmp_path = tf.name

            if not NODE_UPLOADER.exists():
                raise RuntimeError(f"Node uploader not found at {NODE_UPLOADER}")

            cmd = ["node", str(NODE_UPLOADER), tmp_path]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            if not result.stdout.strip():
                raise RuntimeError(f"Uploader returned empty output. stderr:\n{result.stderr}")

            try:
                data = json.loads(result.stdout.strip())
            except json.JSONDecodeError as e:
                raise RuntimeError(f"Uploader did not return valid JSON:\n{result.stdout}\n{result.stderr}") from e

            return {
                "blob_id": data["blobId"],
                "sui_object_id": data["objectId"],
                "walrus_blob_url": data["walrusURL"],
                "walrus_object_url": data["objectURL"],
                "raw_response": data,
            }

        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
