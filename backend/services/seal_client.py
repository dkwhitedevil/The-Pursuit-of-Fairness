# backend/seal/seal_client.py

from typing import Tuple
from sui import SuiClient
from mysten.seal import SealClient
from mysten.sui_bcs import from_hex

# ------------------------------------------------------
# CONFIGURATION — YOU MUST KEEP THESE VALUES
# ------------------------------------------------------

# Your deployed Seal Policy package ID
SEAL_POLICY_PACKAGE = "0xf0ce36656cd421dce66aef95e972e901f21689c3a7ce6402a3b12d4b17eb7b61"

# Your created AllowList shared object ID
ALLOWLIST_OBJECT_ID = "0x85c9763f1fb62d8ff01f33ab681bebf4d7e5891ae18f52a09bb3f01d50b070e6"

# Verified Testnet Key Servers (2-of-N threshold)
KEY_SERVER_IDS = [
    "0x73d05d62c18d9374e3ea529e8e0ed6161da1a141a94d3f76ae3fe4e99356db75",  # Mysten Key Server 1
    "0xf5d14a81a982144ae441cd7d64b09027f116a468bd36e7eca494f750591623c8",  # Mysten Key Server 2
]

# Sui Testnet node
SUI_RPC = "https://fullnode.testnet.sui.io"

# ------------------------------------------------------
# INITIALIZE CLIENTS
# ------------------------------------------------------

# Sui client for Move policy evaluation
sui_client = SuiClient(SUI_RPC)

# Seal Client – this will handle threshold encryption
seal_client = SealClient(
    suiClient=sui_client,
    serverConfigs=[{"objectId": s, "weight": 1} for s in KEY_SERVER_IDS],
    verifyKeyServers=False,
)

# ------------------------------------------------------
# MAIN FUNCTIONS (USED BY BACKEND)
# ------------------------------------------------------

def seal_encrypt(data: bytes, audit_id: str) -> Tuple[bytes, bytes]:
    """
    Encrypt a dataset, model file, or fairness report using Seal.

    audit_id:
        Unique string such as "audit_001", "report_2025_11_21", etc.
        It becomes the identity used for encryption in Seal.

    Returns:
        encrypted_bytes (bytes) – ready to upload to Walrus
        backup_key (bytes) – symmetric DEM fallback key (store or discard)
    """
    encrypted_obj = seal_client.encrypt({
        "threshold": 2,  # Require 2 key servers to decrypt
        "packageId": from_hex(SEAL_POLICY_PACKAGE),
        "id": audit_id.encode("utf-8"),
        "data": data,
    })

    encrypted_bytes = encrypted_obj["encryptedObject"]
    backup_key = encrypted_obj["key"]

    return encrypted_bytes, backup_key


def prepare_identity(audit_number: int) -> str:
    """
    Generates stable identity strings for each encrypted audit item.
    Example: audit_001, audit_002, audit_003...
    """
    return f"audit_{audit_number:03d}"


# ------------------------------------------------------
# OPTIONAL — STORE BACKUP KEYS (IF NEEDED FOR EMERGENCY)
# ------------------------------------------------------

def store_backup_key(audit_id: str, key: bytes):
    """
    Optional fallback: write the backup key to local storage.
    Not required for Seal, but useful for emergency recovery.
    """
    with open(f"backend/tmp/{audit_id}_backup.key", "wb") as f:
        f.write(key)
