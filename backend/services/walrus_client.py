from pathlib import Path
import subprocess, tempfile, json, os

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

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if not stdout:
            raise RuntimeError(f"Upload failed: {stderr}")

        # ---- Render fix: parse ONLY the last JSON line ----
        last_line = stdout.split("\n")[-1].strip()

        try:
            return json.loads(last_line)
        except Exception:
            raise RuntimeError(
                f"Invalid JSON received.\n\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"
            )
