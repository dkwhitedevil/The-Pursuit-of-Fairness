import os
import time
import base64
from typing import Dict, Any, List, Optional

# ----------------------------
# SUI CONFIG
# ----------------------------
SUI_RPC = os.getenv("SUI_RPC", "https://fullnode.testnet.sui.io")
PACKAGE_ID = os.getenv("SUI_PACKAGE_ID")
TABLE_ID = os.getenv("SUI_TABLE_ID")
MODULE_NAME = os.getenv("SUI_MODULE", "oracle")
FUNCTION_NAME = os.getenv("SUI_FUNCTION", "anchor_audit")

SUI_PRIVATE_KEY = os.getenv("SUI_PRIVATE_KEY")        # hex, 64 chars (32 bytes)
SUI_SIGNER_ADDRESS = os.getenv("SUI_SIGNER_ADDRESS")  # 0x...
SUI_GAS_OBJECT_ID = os.getenv("SUI_GAS_OBJECT_ID")    # 0x...


# --------------------------------------------------------------
# Walrus blobId is base64url, not hex
# --------------------------------------------------------------
def decode_blobid(blobid: str) -> List[int]:
    blobid = blobid.strip().replace("\n", "")
    padding = "=" * (-len(blobid) % 4)
    raw = base64.urlsafe_b64decode(blobid + padding)
    return list(raw)


# --------------------------------------------------------------
# Build move-call args
# --------------------------------------------------------------
def build_args(blob_hash: str, fairness_score: int, timestamp: int):
    return [
        TABLE_ID,
        decode_blobid(blob_hash),
        int(fairness_score),
        int(timestamp),
    ]


# --------------------------------------------------------------
# Try variants of pysui imports used across versions
# Return a tuple (ClientClass, key_factory, tx_factory)
# ClientClass is the class (not instance) for SuiClient
# key_factory: callable(bytes) -> signing_key_object
# tx_factory: callable(client) -> tx_builder (with move_call and sign_and_execute)
# --------------------------------------------------------------
def _try_load_pysui():
    # variant 1: newer pysui structure (0.9x+)
    try:
        from pysui.sui.sui_clients.sync_client import SuiClient as ClientClass
        # Key factories
        key_factory = None
        try:
            from pysui.sui.sui_crypto import Ed25519PrivateKey as _EdKey
            key_factory = lambda b: _EdKey.from_private_bytes(b)
        except Exception:
            try:
                from pysui.sui.sui_crypto import SuiPrivateKey as _SuiKey
                key_factory = lambda b: _SuiKey(b)
            except Exception:
                key_factory = None

        # txn wrappers
        tx_factory = None
        try:
            from pysui.sui.sui_txn import SyncTransaction as _SyncTxn
            tx_factory = lambda c: _SyncTxn(c)
        except Exception:
            try:
                from pysui.sui.sui_txn import SyncTxn as _SyncTxn2
                tx_factory = lambda c: _SyncTxn2(c)
            except Exception:
                tx_factory = None

        return (ClientClass, key_factory, tx_factory)
    except Exception:
        pass

    # variant 2: older single-module pysui
    try:
        import pysui
        ClientClass = getattr(pysui, "SuiClient", None)

        key_factory = None
        for name in ("Ed25519PrivateKey", "SuiPrivateKey", "PrivateKey"):
            if hasattr(pysui, name):
                cls = getattr(pysui, name)
                # prefer from_private_bytes if available
                key_factory = lambda b, cls=cls: cls.from_private_bytes(b) if hasattr(cls, "from_private_bytes") else cls(b)
                break

        tx_factory = None
        for name in ("SyncTransaction", "SyncTxn", "Transaction"):
            if hasattr(pysui, name):
                cls = getattr(pysui, name)
                tx_factory = lambda c, cls=cls: cls(c)
                break

        if ClientClass:
            return (ClientClass, key_factory, tx_factory)
    except Exception:
        pass

    return (None, None, None)


# --------------------------------------------------------------
# Convert unsigned payload (for client-side signing) — shape used by frontend
# --------------------------------------------------------------
def build_unsigned_payload(blob_hash: str, fairness_score: int, timestamp: int) -> Dict[str, Any]:
    args = build_args(blob_hash, fairness_score, timestamp)
    return {
        "packageObjectId": PACKAGE_ID,
        "module": MODULE_NAME,
        "function": FUNCTION_NAME,
        "typeArguments": [],
        "arguments": args,
        "gasBudget": 10000000,
    }


# --------------------------------------------------------------
# MAIN: SERVER-SIDE signing (best-effort). On any failure return unsigned payload
# --------------------------------------------------------------
def anchor_audit_on_sui(walrus_info: Dict[str, Any], fairness_score: float) -> Dict[str, Any]:
    blob_hash = walrus_info.get("blobId") or walrus_info.get("blob_id")
    if not blob_hash:
        raise ValueError("missing blobId from walrus_info")

    timestamp = int(time.time())
    fairness_score = int(fairness_score or 0)

    unsigned = build_unsigned_payload(blob_hash, fairness_score, timestamp)

    # If server signer isn't configured, return unsigned payload
    if not (SUI_PRIVATE_KEY and SUI_SIGNER_ADDRESS and SUI_GAS_OBJECT_ID):
        return {
            "status": "unsigned",
            "message": "Server signer not configured; returning unsigned payload.",
            "payload": unsigned,
            "proof": {"bundle_hash": blob_hash, "fairness_score": fairness_score, "timestamp": timestamp},
        }

    # Try load pysui variants (returns classes/factories)
    ClientClass, key_factory, tx_factory = _try_load_pysui()
    if ClientClass is None:
        return {
            "status": "unsigned",
            "message": "pysui client not available or incompatible; returning unsigned payload.",
            "payload": unsigned,
            "proof": {"bundle_hash": blob_hash, "fairness_score": fairness_score, "timestamp": timestamp},
        }

    try:
        # ----- IMPORTANT FIX: instantiate client with config when required -----
        cfg = None
        try:
            # newer pysui exposes SuiConfig; prefer using it so SuiClient(cfg) works
            from pysui.sui.sui_config import SuiConfig
            # Try to set RPC override when available
            try:
                cfg = SuiConfig.default_config()
                # If SUI_RPC differs from default, try to set endpoint if API allows
                # (ignore failures — not all pysui versions expose settable fields)
                try:
                    if hasattr(cfg, "rpc"):
                        cfg.rpc = SUI_RPC
                except Exception:
                    pass
            except Exception:
                cfg = None
        except Exception:
            cfg = None

        # Try instantiating ClientClass with cfg, but gracefully fallback to zero-arg
        try:
            client = ClientClass(cfg) if cfg is not None else ClientClass()
        except TypeError:
            # constructor didn't accept cfg (older pysui), try zero-arg
            client = ClientClass()

        # Build key object
        seed_bytes = bytes.fromhex(SUI_PRIVATE_KEY)
        if key_factory is None:
            # no signing helper available; fallback to unsigned
            return {
                "status": "unsigned",
                "message": "pysui missing key constructor; returning unsigned payload.",
                "payload": unsigned,
                "proof": {"bundle_hash": blob_hash, "fairness_score": fairness_score, "timestamp": timestamp},
            }

        signer = key_factory(seed_bytes)

        # If tx factory available, try the convenient builder path
        if tx_factory is not None:
            tx = tx_factory(client)
            # Many pysui txn wrappers provide move_call; if not, we'll fallback
            if hasattr(tx, "move_call"):
                tx.move_call(
                    target=f"{PACKAGE_ID}::{MODULE_NAME}::{FUNCTION_NAME}",
                    arguments=build_args(blob_hash, fairness_score, timestamp),
                    gas=SUI_GAS_OBJECT_ID,
                    gas_budget=10_000_000,
                    sender=SUI_SIGNER_ADDRESS,
                )
                # sign and execute if method available
                if hasattr(tx, "sign_and_execute"):
                    result = tx.sign_and_execute(signer)
                    # normalize a safe response
                    digest = getattr(result, "digest", None) or (result.get("digest") if isinstance(result, dict) else None)
                    effects = getattr(result, "effects", None) or (result.get("effects") if isinstance(result, dict) else None)
                    events = getattr(result, "events", None) or (result.get("events") if isinstance(result, dict) else None)
                    return {
                        "status": "submitted",
                        "tx_digest": digest,
                        "effects": effects,
                        "events": events,
                        "proof": {"bundle_hash": blob_hash, "fairness_score": fairness_score, "timestamp": timestamp},
                        "explorer": f"https://suiscan.xyz/testnet/tx/{digest}" if digest else None,
                    }
                else:
                    # cannot sign+execute with this txn wrapper
                    return {
                        "status": "unsigned",
                        "message": "pysui txn builder lacks sign_and_execute; returning unsigned payload.",
                        "payload": unsigned,
                        "proof": {"bundle_hash": blob_hash, "fairness_score": fairness_score, "timestamp": timestamp},
                    }

        # If we reach here, can't use txn builder — fallback to unsigned
        return {
            "status": "unsigned",
            "message": "Could not perform server-side signing with available pysui APIs; returning unsigned payload.",
            "payload": unsigned,
            "proof": {"bundle_hash": blob_hash, "fairness_score": fairness_score, "timestamp": timestamp},
        }

    except Exception as e:
        # On *any* error, return unsigned payload and the error details for debugging
        return {
            "status": "error",
            "message": "Server-side signing failed (falling back to unsigned payload).",
            "details": str(e),
            "payload": unsigned,
            "proof": {"bundle_hash": blob_hash, "fairness_score": fairness_score, "timestamp": timestamp},
        }
