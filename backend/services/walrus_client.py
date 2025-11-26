import subprocess
import tempfile
import json
import os
from pathlib import Path

NODE_UPLOADER = Path(__file__).parent.parent / "walrus-uploader" / "upload.js"

class WalrusClient:
    def upload_blob(self, bytes_data: bytes, filename: str = "bundle.json"):
        tmp_path = None

        try:
            with tempfile.NamedTemporaryFile(delete=False) as tf:
                tf.write(bytes_data)
                tf.flush()
                tmp_path = tf.name

            if not NODE_UPLOADER.exists():
                raise RuntimeError(f"Node uploader not found: {NODE_UPLOADER}")

            result = subprocess.run(
                ["node", str(NODE_UPLOADER), tmp_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"Walrus upload failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
                )

            # ░░░ FIX: Extract only JSON from last line ░░░
            last = result.stdout.strip().split("\n")[-1]

            return json.loads(last)

        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
