import os
import time
import base64
import requests
from nacl.signing import SigningKey
from nacl.encoding import RawEncoder

SUI_RPC = os.getenv("SUI_RPC", "https://fullnode.testnet.sui.io")
PACKAGE_ID = os.getenv("SUI_PACKAGE_ID")
MODULE_NAME = os.getenv("SUI_MODULE", "oracle")
FUNCTION_NAME = os.getenv("SUI_FUNCTION", "anchor_audit")
TABLE_ID = os.getenv("SUI_TABLE_ID")

SIGNER_ADDRESS = os.getenv("SUI_SIGNER_ADDRESS")
PRIVATE_KEY_HEX = os.getenv("SUI_PRIVATE_KEY")
GAS_OBJECT_ID = os.getenv("SUI_GAS_OBJECT_ID")
GAS_VERSION = int(os.getenv("GAS_VERSION", "349181017"))
GAS_DIGEST = os.getenv("GAS_DIGEST", "DbEbvQ5JXAavVKgkfgtoRhE3zB4zfnyjifRNGM6eerpf")


def decode_blobid(blobid):
    padding = "=" * (-len(blobid) % 4)
    return list(base64.urlsafe_b64decode(blobid + padding))

def build_ptb(blob_hash, fairness_score, timestamp):
    return {
        "kind": "ProgrammableTransaction",
        "transaction": {
            "sender": SIGNER_ADDRESS,
            "inputs": [
                {"type": "pure", "value": TABLE_ID},                    # 0
                {"type": "pure", "value": decode_blobid(blob_hash)},    # 1
                {"type": "pure", "value": fairness_score},              # 2
                {"type": "pure", "value": timestamp},                   # 3
                {"type": "object", "objectId": GAS_OBJECT_ID},          # 4
            ],
            "commands": [
                {
                    "MoveCall": {
                        "package": PACKAGE_ID,
                        "module": MODULE_NAME,
                        "function": FUNCTION_NAME,
                        "typeArguments": [],
                        "arguments": [0, 1, 2, 3, 4],                   # FIXED
                    }
                }
            ],
            "gasPayment": [
                {
                    "objectId": GAS_OBJECT_ID,
                    "version": GAS_VERSION,
                    "digest": GAS_DIGEST,
                }
            ],
            "gasBudget": 10000000,
            "expiration": None,
        },
    }


def sign_bytes(bcs_bytes):
    sk = SigningKey(bytes.fromhex(PRIVATE_KEY_HEX), encoder=RawEncoder)
    sig = sk.sign(bcs_bytes).signature
    return b"\x00" + sig  # Ed25519 prefix


def anchor_audit_on_sui(walrus_info, fairness_score):
    blob_hash = walrus_info.get("blobId") or walrus_info.get("blob_id")
    if not blob_hash:
        raise ValueError("blobId missing")

    timestamp = int(time.time())
    fairness_score = int(fairness_score)

    ptb = build_ptb(blob_hash, fairness_score, timestamp)

    # Serialize PTB
    ser_res = requests.post(SUI_RPC, json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "sui_serializeTransactionBlock",
        "params": [ptb, "Latest"],
    }).json()

    if "error" in ser_res:
        return {"status": "error", "details": ser_res["error"]}

    bcs_bytes = base64.b64decode(ser_res["result"])
    signature_b64 = base64.b64encode(sign_bytes(bcs_bytes)).decode()

    # Execute
    exec_res = requests.post(SUI_RPC, json={
        "jsonrpc": "2.0",
        "id": 2,
        "method": "sui_executeTransactionBlock",
        "params": [
            base64.b64encode(bcs_bytes).decode(),
            [signature_b64],
            SIGNER_ADDRESS,
            {"showEffects": True, "showEvents": True},
        ],
    }).json()

    if "error" in exec_res:
        return {"status": "error", "details": exec_res["error"]}

    digest = exec_res["result"]["digest"]

    return {
        "status": "submitted",
        "digest": digest,
        "explorer": f"https://suiscan.xyz/testnet/tx/{digest}",
        "proof": {
            "bundle_hash": blob_hash,
            "fairness_score": fairness_score,
            "timestamp": timestamp,
        }
    }
