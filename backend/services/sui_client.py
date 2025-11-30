# backend/services/sui_client.py
import os
import time
import base64
from typing import Dict, Any

# ----------------------------
# SUI CONFIG
# ----------------------------
SUI_RPC = os.getenv("SUI_RPC", "https://fullnode.testnet.sui.io")
PACKAGE_ID = os.getenv("SUI_PACKAGE_ID")
TABLE_ID = os.getenv("SUI_TABLE_ID")
MODULE_NAME = os.getenv("SUI_MODULE", "oracle")
FUNCTION_NAME = os.getenv("SUI_FUNCTION", "anchor_audit")

SUI_PRIVATE_KEY = os.getenv("SUI_PRIVATE_KEY")        # hex, 64 chars
SUI_SIGNER_ADDRESS = os.getenv("SUI_SIGNER_ADDRESS")  # 0x...
SUI_GAS_OBJECT_ID = os.getenv("SUI_GAS_OBJECT_ID")    # 0x...


# --------------------------------------------------------------
# Walrus blobId is base64url, not hex
# --------------------------------------------------------------
def decode_blobid(blobid: str) -> list[int]:
    blobid = blobid.strip().replace("\n", "")
    padding = "=" * (-len(blobid) % 4)
    raw = base64.urlsafe_b64decode(blobid + padding)
    return list(raw)


# --------------------------------------------------------------
# Build moving call args
# --------------------------------------------------------------
def build_args(blob_hash: str, fairness_score: int, timestamp: int):
    return [
        TABLE_ID,
        decode_blobid(blob_hash),
        int(fairness_score),
        int(timestamp),
    ]


# --------------------------------------------------------------
# MAIN: SERVER-SIDE SIGNING USING LATEST pysui
# --------------------------------------------------------------
def anchor_audit_on_sui(walrus_info: Dict[str, Any], fairness_score: float):
    blob_hash = (
        walrus_info.get("blobId")
        or walrus_info.get("blob_id")
        or None
    )
    if not blob_hash:
        raise ValueError("missing blobId from walrus_info")

    timestamp = int(time.time())
    fairness_score = int(fairness_score or 0)

    try:
        # Import newest pysui API
        from pysui.sui.sui_clients.sync_client import SuiClient
        from pysui.sui.sui_crypto import Ed25519PrivateKey
        from pysui.sui.sui_txn import SyncTransaction

        client = SuiClient(SUI_RPC)

        # Load private key
        key_bytes = bytes.fromhex(SUI_PRIVATE_KEY)
        priv = Ed25519PrivateKey.from_private_bytes(key_bytes)

        # Build transaction
        tx = SyncTransaction(client)

        tx.move_call(
            target=f"{PACKAGE_ID}::{MODULE_NAME}::{FUNCTION_NAME}",
            arguments=build_args(blob_hash, fairness_score, timestamp),
            gas=SUI_GAS_OBJECT_ID,
            gas_budget=10_000_000,
            sender=SUI_SIGNER_ADDRESS,
        )

        # Sign + submit
        result = tx.sign_and_execute(priv)

        return {
            "status": "submitted",
            "tx_digest": result.digest,
            "effects": result.effects,
            "events": result.events,
            "proof": {
                "bundle_hash": blob_hash,
                "fairness_score": fairness_score,
                "timestamp": timestamp,
            },
            "explorer": f"https://suiscan.xyz/testnet/tx/{result.digest}"
        }

    except Exception as e:
        return {
            "status": "error",
            "message": "Sui server signing failed",
            "details": str(e),
            "proof": {
                "bundle_hash": blob_hash,
                "fairness_score": fairness_score,
                "timestamp": timestamp,
            }
        }
