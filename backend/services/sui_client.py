import subprocess
import json
import time
from typing import Dict, Any


# -----------------------------------------
# CONSTANTS: YOUR DEPLOYED CONTRACT INFO
# -----------------------------------------

PACKAGE_ID = "0x41ec79c3295647a41c0d6a725116be696df361d8789d2ee71284e1e034f2df40"
TABLE_ID = "0x3f65bc27fd881f1d1f9ebea9d2c30cbce9f6c981dd691a2b545b5180df94841d"

MODULE_NAME = "oracle"
FUNCTION_NAME = "anchor_audit"


# -----------------------------------------
# EXECUTION HELPER
# -----------------------------------------

def run_sui_command(cmd: list) -> Dict[str, Any]:
    """Executes a Sui CLI command and returns stdout + stderr."""

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    return {
        "command": " ".join(cmd),
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode
    }


# -----------------------------------------
# HELPER: convert hex to vector<u8>
# -----------------------------------------

def hex_to_u8_vector(hex_str: str) -> str:
    """
    Converts a hex string into CLI-compatible vector<u8> format.
    Example:
        hex 'abcd01' -> '[171,205,1]'
    """
    hex_str = hex_str.lower().replace("0x", "").strip()
    if len(hex_str) % 2 != 0:
        hex_str = "0" + hex_str

    b = hex_str.encode("utf-8")
    return "[" + ",".join(str(v) for v in b) + "]"


# -----------------------------------------
# MAIN ANCHOR FUNCTION
# -----------------------------------------

def anchor_audit_on_sui(walrus_info: Dict[str, Any], fairness_score: float) -> Dict[str, Any]:
    """
    Anchors an audit proof on Sui blockchain.

    Required Move args:
      table: &mut AuditTable
      bundle_hash: vector<u8>
      fairness_score: u64
      timestamp: u64
    """

    # Your main.py passes `walrus_info` directly → get blob ID here
    blob_hash = walrus_info.get("blobId") or walrus_info.get("blob_id")

    if not blob_hash:
        raise ValueError("No blobId found in walrus_info. Cannot anchor on Sui.")

    timestamp = int(time.time())

    # Convert blob hash → vector<u8>
    blob_vec = hex_to_u8_vector(blob_hash)

    # -----------------------------------------
    # SUI CALL ARGUMENTS MUST MATCH MOVE EXACTLY
    # -----------------------------------------

    cmd = [
        "sui", "client", "call",
        "--package", PACKAGE_ID,
        "--module", MODULE_NAME,
        "--function", FUNCTION_NAME,
        "--args",
            TABLE_ID,             # &mut AuditTable
            json.dumps(blob_vec),             # vector<u8>
            str(int(fairness_score)),
            str(timestamp),
        "--gas-budget", "150000000"
    ]

    result = run_sui_command(cmd)

    # -----------------------------------------
    # Build frontend response
    # -----------------------------------------

    proof = {
        "blob_hash": blob_hash,
        "fairness_score": fairness_score,
        "timestamp": timestamp,
    }

    return {
        "status": "submitted",
        "proof": proof,
        "sui_raw": result
    }
