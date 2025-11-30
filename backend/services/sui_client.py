# backend/services/sui_client.py
import os
import time
from typing import Dict, Any

# Sui RPC + Contract Config
SUI_RPC = os.getenv("SUI_RPC", "https://fullnode.testnet.sui.io")
PACKAGE_ID = os.getenv("SUI_PACKAGE_ID")
TABLE_ID = os.getenv("SUI_TABLE_ID")
MODULE_NAME = os.getenv("SUI_MODULE", "oracle")
FUNCTION_NAME = os.getenv("SUI_FUNCTION", "anchor_audit")

# Server-side signer config
SUI_PRIVATE_KEY = os.getenv("SUI_PRIVATE_KEY")          # 32-byte hex seed (NO 0x prefix)
SUI_SIGNER_ADDRESS = os.getenv("SUI_SIGNER_ADDRESS")    # 0x...
SUI_GAS_OBJECT_ID = os.getenv("SUI_GAS_OBJECT_ID")      # 0x...


def _build_move_call_args(blob_hash_hex: str, fairness_score: int, timestamp: int):
    """
    Convert hex blob hash into vector<u8> and build Move call arguments.
    """
    h = blob_hash_hex.lower().replace("0x", "")
    if len(h) % 2 != 0:
        h = "0" + h

    blob_bytes = [int(h[i:i+2], 16) for i in range(0, len(h), 2)]
    return [
        TABLE_ID,          # &mut AuditTable
        blob_bytes,        # vector<u8> bundle hash
        int(fairness_score),
        int(timestamp)
    ]


def _rpc_move_call_payload(blob_hash_hex: str, fairness_score: int, timestamp: int):
    """
    Returns an unsigned payload suitable for Sui Wallet signing.
    """
    args = _build_move_call_args(blob_hash_hex, fairness_score, timestamp)

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
    Anchors a fairness audit proof on the Sui blockchain.

    Behavior:
      - If server signer configured: automatically signs + submits.
      - Otherwise returns unsigned payload for client-side signing.
    """
    blob_hash = walrus_info.get("blobId") or walrus_info.get("blob_id")
    if not blob_hash:
        raise ValueError("walrus_info missing blobId")

    timestamp = int(time.time())
    fairness_score = int(fairness_score or 0)

    move_call = _rpc_move_call_payload(blob_hash, fairness_score, timestamp)

    # If no server keys -> return unsigned payload
    if not (SUI_PRIVATE_KEY and SUI_SIGNER_ADDRESS and SUI_GAS_OBJECT_ID):
        return {
            "status": "unsigned",
            "message": "Server has no Sui signer configured.",
            "payload": move_call,
            "proof": {
                "bundle_hash": blob_hash,
                "fairness_score": fairness_score,
                "timestamp": timestamp
            }
        }

    # ------------------------------
    # Server-side signing (pysui)
    # ------------------------------
    try:
        from pysui import SuiClient
        from pysui.sui.sui_crypto import Ed25519PrivateKey

        client = SuiClient(SUI_RPC)

        # Build keypair from 32-byte seed
        seed_bytes = bytes.fromhex(SUI_PRIVATE_KEY)
        priv = Ed25519PrivateKey.from_private_bytes(seed_bytes)

        # Build Move Call transaction
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

        # Submit transaction
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
            "message": "Server-side signing failed.",
            "details": str(e),
            "unsigned_payload": move_call,
            "proof": {
                "bundle_hash": blob_hash,
                "fairness_score": fairness_score,
                "timestamp": timestamp
            }
        }
