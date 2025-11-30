# backend/services/sui_client.py
import os
import time
import base64
from typing import Dict, Any

# Sui RPC + Contract Config
SUI_RPC = os.getenv("SUI_RPC", "https://fullnode.testnet.sui.io")
PACKAGE_ID = os.getenv("SUI_PACKAGE_ID")
TABLE_ID = os.getenv("SUI_TABLE_ID")
MODULE_NAME = os.getenv("SUI_MODULE", "oracle")
FUNCTION_NAME = os.getenv("SUI_FUNCTION", "anchor_audit")

# Server-side signer config
SUI_PRIVATE_KEY = os.getenv("SUI_PRIVATE_KEY")          # hex seed, no 0x
SUI_SIGNER_ADDRESS = os.getenv("SUI_SIGNER_ADDRESS")    # 0x...
SUI_GAS_OBJECT_ID = os.getenv("SUI_GAS_OBJECT_ID")      # 0x...


# -----------------------------------------------------------
# FIXED: Walrus blobId is BASE64URL, NOT hex.
# -----------------------------------------------------------
def decode_walrus_blobid(blobid: str) -> list[int]:
    """
    Walrus blobId is base64url-encoded, not hex.
    Convert to raw bytes → vector<u8>.
    """
    blobid = blobid.strip()
    padding = "=" * (-len(blobid) % 4)
    raw = base64.urlsafe_b64decode(blobid + padding)
    return list(raw)


def _build_move_call_args(blob_hash: str, fairness_score: int, timestamp: int):
    """
    Build Move call arguments with correct vector<u8> decoded from Walrus blobId.
    """
    blob_bytes = decode_walrus_blobid(blob_hash)

    return [
        TABLE_ID,          # &mut AuditTable
        blob_bytes,        # vector<u8>
        int(fairness_score),
        int(timestamp)
    ]


def _rpc_move_call_payload(blob_hash: str, fairness_score: int, timestamp: int):
    """
    Creates unsigned Move call payload for client or server signing.
    """
    args = _build_move_call_args(blob_hash, fairness_score, timestamp)

    return {
        "packageObjectId": PACKAGE_ID,
        "module": MODULE_NAME,
        "function": FUNCTION_NAME,
        "typeArguments": [],
        "arguments": args,
        "gasBudget": 10000000,
    }


def anchor_audit_on_sui(walrus_info: Dict[str, Any], fairness_score: float) -> Dict[str, Any]:
    """
    Anchors a fairness audit proof on Sui.
    """
    blob_hash = walrus_info.get("blobId") or walrus_info.get("blob_id")
    if not blob_hash:
        raise ValueError("walrus_info missing blobId")

    timestamp = int(time.time())
    fairness_score = int(fairness_score or 0)

    move_call = _rpc_move_call_payload(blob_hash, fairness_score, timestamp)

    # -----------------------------------------
    # If NO server signer → return unsigned data
    # -----------------------------------------
    if not (SUI_PRIVATE_KEY and SUI_SIGNER_ADDRESS and SUI_GAS_OBJECT_ID):
        return {
            "status": "unsigned",
            "message": "Server signer missing. Returning unsigned payload.",
            "payload": move_call,
            "proof": {
                "bundle_hash": blob_hash,
                "fairness_score": fairness_score,
                "timestamp": timestamp
            }
        }

    # -----------------------------------------
    # Server-side signing using pysui
    # -----------------------------------------
    try:
        from pysui import SuiClient
        from pysui.sui.sui_crypto import Ed25519PrivateKey

        client = SuiClient(SUI_RPC)

        # Load private key (must be 32-byte seed)
        seed = bytes.fromhex(SUI_PRIVATE_KEY)
        priv = Ed25519PrivateKey.from_private_bytes(seed)

        # Build transaction
        tx = client.build_move_call_transaction(
            package=PACKAGE_ID,
            module=MODULE_NAME,
            function=FUNCTION_NAME,
            type_arguments=[],
            arguments=move_call["arguments"],
            gas_budget=move_call["gasBudget"],
            sender=SUI_SIGNER_ADDRESS,
            gas_object=SUI_GAS_OBJECT_ID
        )

        # Sign raw bytes
        signature = priv.sign(tx.bytes)

        # Submit to chain
        resp = client.execute_transaction_block(
            tx_bytes=tx.bytes,
            signature=signature,
            sender=SUI_SIGNER_ADDRESS,
            request_type="WaitForLocalExecution"
        )

        return {
            "status": "submitted",
            "response": resp,
            "proof": {
                "bundle_hash": blob_hash,
                "fairness_score": fairness_score,
                "timestamp": timestamp
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "message": "Server-side signing failed",
            "details": str(e),
            "unsigned_payload": move_call,
            "proof": {
                "bundle_hash": blob_hash,
                "fairness_score": fairness_score,
                "timestamp": timestamp
            }
        }
