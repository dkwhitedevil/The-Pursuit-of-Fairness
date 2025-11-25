# backend/services/seal_node_bridge.py

import subprocess
import json
import os
import uuid

TMP_DIR = os.path.join(os.getcwd(), "tmp")
os.makedirs(TMP_DIR, exist_ok=True)


def prepare_identity(_: int = None) -> str:
    """Generate a unique human-safe audit identity."""
    return f"audit_{uuid.uuid4().hex}"


def seal_encrypt_node(input_path: str, identity: str):
    """
    Runs the Node.js SEAL client with proper flags for Node 22.
    """

    NODE = "/home/dk/.nvm/versions/node/v22.21.1/bin/node"

    result = subprocess.run(
        [
            NODE,
            "--experimental-global-webcrypto",
            "--experimental-modules",
            "--no-warnings",
            "backend/services/seal_client.js",
            input_path,
            identity,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Seal encryption failed:\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

    # --- Extract JSON line ---
    json_line = None
    for line in result.stdout.splitlines():
        line_strip = line.strip()
        if line_strip.startswith("{") and line_strip.endswith("}"):
            json_line = line_strip
            break

    if not json_line:
        raise RuntimeError(
            f"Seal client did not output valid JSON.\n"
            f"Output was:\n{result.stdout}"
        )

    data = json.loads(json_line)

    encrypted_b64 = data["encryptedObject"]
    backup_key = data["backupKey"]
    identity_out = data.get("identity", identity)
    return identity_out, encrypted_b64, backup_key
