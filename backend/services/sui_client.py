# backend/services/sui_client.py
import os
import time
import json
import requests
from typing import Dict, Any, Optional

# Constants (keep as set in your app)
SUI_RPC = os.getenv("SUI_RPC", "https://fullnode.testnet.sui.io")
PACKAGE_ID = os.getenv("SUI_PACKAGE_ID", "0x41ec79c3295647a41c0d6a725116be696df361d8789d2ee71284e1e034f2df40")
TABLE_ID = os.getenv("SUI_TABLE_ID", "0x3f65bc27fd881f1d1f9ebea9d2c30cbce9f6c981dd691a2b545b5180df94841d")
MODULE_NAME = os.getenv("SUI_MODULE", "oracle")
FUNCTION_NAME = os.getenv("SUI_FUNCTION", "anchor_audit")

# Optional server-side signer config (if set, will attempt to sign and submit)
SUI_PRIVATE_KEY = os.getenv("SUI_PRIVATE_KEY")  # hex or base64, *must* match pysui expected format
SUI_SIGNER_ADDRESS = os.getenv("SUI_SIGNER_ADDRESS")
# Optionally set a gas object id which will be used when signing (if required)
SUI_GAS_OBJECT_ID = os.getenv("SUI_GAS_OBJECT_ID")


def _build_move_call_args(blob_hash_hex: str, fairness_score: int, timestamp: int):
    """
    Return the arguments array for the move call for the RPC payload.
    Depending on the exact move types your contract expects, you might need
    to encode the bundle hash as vector<u8> or a string; adjust below.
    We'll send the raw hex string as bytes vector encoded as an array of ints.
    """
    # Convert hex string -> list of ints (vector<u8>)
    h = blob_hash_hex.lower().replace("0x", "")
    if len(h) % 2 != 0:
        h = "0" + h
    blob_bytes = [int(h[i : i + 2], 16) for i in range(0, len(h), 2)]

    # RPC expects arguments serializable to JSON. For moveCall via RPC, we will provide:
    # arguments: [ table_id, <vector<u8> as list>, fairness_score, timestamp ]
    return [TABLE_ID, blob_bytes, int(fairness_score), int(timestamp)]


def _rpc_move_call_payload(blob_hash_hex: str, fairness_score: int, timestamp: int):
    """
    Create a raw RPC payload for the move call. This payload can be returned to a caller
    for signing/submit, or used to sign here (if server-side signer is configured).
    """
    args = _build_move_call_args(blob_hash_hex, fairness_score, timestamp)
    # Using the 'sui_executeTransactionBlock' RPC requires a signed transaction block,
    # so here we instead prepare a 'moveCall' transaction descriptor that clients can sign.
    # We'll return a JSON object that contains the necessary fields to sign.
    move_call = {
        "packageObjectId": PACKAGE_ID,
        "module": MODULE_NAME,
        "function": FUNCTION_NAME,
        "typeArguments": [],
        "arguments": args,
        "gasBudget": 10000000
    }
    return move_call


def anchor_audit_on_sui(walrus_info: Dict[str, Any], fairness_score: float) -> Dict[str, Any]:
    """
    Anchor the given walrus_info blob hash and fairness score on Sui.

    Behavior:
      - If SUI_PRIVATE_KEY and SUI_SIGNER_ADDRESS are set, attempt to sign and submit using pysui.
      - Otherwise return an unsigned payload that an operator/wallet can sign & submit.

    Returns a dict describing the submission state. If unsigned, returns `{"status":"unsigned","payload": ...}`.
    """
    blob_hash = walrus_info.get("blobId") or walrus_info.get("blob_id")
    if not blob_hash:
        raise ValueError("No blobId found in walrus_info. Cannot anchor on Sui.")

    timestamp = int(time.time())

    # prepare move call payload
    move_call = _rpc_move_call_payload(blob_hash, fairness_score or 0, timestamp)

    # If no server-side signer configured, return the unsigned payload to the caller
    if not (SUI_PRIVATE_KEY and SUI_SIGNER_ADDRESS):
        return {
            "status": "unsigned",
            "message": "No server signer configured. This payload must be signed and submitted by a Sui wallet or CLI.",
            "payload": move_call,
            "proof": {"blob_hash": blob_hash, "fairness_score": fairness_score, "timestamp": timestamp}
        }

    # Otherwise attempt to sign & submit using pysui
    try:
        # Defer import until needed so deployments without pysui won't fail at import time
        from pysui import SuiClient, Keypair, Signer, rpc
        from pysui.sui.sui_types import SuiAddress

        client = SuiClient(SUI_RPC)

        # Create Keypair from private key. The exact constructor depends on format.
        # pysui typically expects an Ed25519 private key object or hex seed. You must
        # ensure SUI_PRIVATE_KEY is provided in the correct format for pysui.
        # This code assumes SUI_PRIVATE_KEY is a hex-encoded seed/private key usable by pysui.
        kp = Keypair.from_private_key_hex(SUI_PRIVATE_KEY)  # may need to change depending on pysui version
        signer = Signer(kp, SUI_SIGNER_ADDRESS)

        # Build a transaction block for a Move call
        tx = client.build_move_call_transaction(
            package=PACKAGE_ID,
            module=MODULE_NAME,
            function=FUNCTION_NAME,
            type_arguments=[],
            arguments=move_call["arguments"],
            gas_budget=move_call.get("gasBudget", 10000000),
            sender=SUI_SIGNER_ADDRESS,
            gas_object=SUI_GAS_OBJECT_ID
        )

        # Sign and submit
        signed = signer.sign_transaction_block(tx)
        resp = client.execute_transaction_block(signed, request_type="WaitForLocalExecution")

        return {
            "status": "submitted",
            "response": resp,
            "proof": {"blob_hash": blob_hash, "fairness_score": fairness_score, "timestamp": timestamp}
        }

    except Exception as e:
        # return helpful debug info
        return {
            "status": "error",
            "message": "Server-side signing failed. See 'details'. If you don't want server signing, remove SUI_PRIVATE_KEY or set it empty.",
            "details": str(e),
            "unsigned_payload": move_call,
            "proof": {"blob_hash": blob_hash, "fairness_score": fairness_score, "timestamp": timestamp}
        }
