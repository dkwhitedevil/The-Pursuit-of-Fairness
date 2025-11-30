import subprocess
import tempfile
import json
import os
from pathlib import Path

NODE_UPLOADER = Path(__file__).parent / "walrus-uploader" / "upload.js"

class WalrusClient:
    def upload_blob(self, bytes_data: bytes, filename="blob.bin"):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".bin")
        tmp.write(bytes_data)
        tmp.close()

        cmd = ["node", str(NODE_UPLOADER), tmp.name]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        os.remove(tmp.name)

        if not result.stdout:
            raise RuntimeError("Upload failed: " + result.stderr)

        return json.loads(result.stdout)
