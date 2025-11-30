from pathlib import Path
import subprocess, tempfile, json, os

# Always correct, even inside Docker
NODE_UPLOADER = Path("/app/walrus-uploader/upload.js")

class WalrusClient:
    def upload_blob(self, bytes_data: bytes, filename="blob.bin"):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".bin")
        tmp.write(bytes_data)
        tmp.close()

        if not NODE_UPLOADER.exists():
            raise RuntimeError(f"Node uploader not found at {NODE_UPLOADER}")

        cmd = ["node", str(NODE_UPLOADER), tmp.name]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        os.remove(tmp.name)

        if not result.stdout:
            raise RuntimeError("Upload failed: " + result.stderr)

        return json.loads(result.stdout)
