# backend/services/sui_reader.py
import requests
import json
from typing import List, Dict

# Change if you want a different RPC node
SUI_RPC = "https://fullnode.testnet.sui.io"
SUI_TABLE_ID = "0x3f65bc27fd881f1d1f9ebea9d2c30cbce9f6c981dd691a2b545b5180df94841d"

def _to_hex_from_u8_list(u8_list):
    # convert list of ints -> hex string (two hex chars per byte)
    return "".join(format(int(b) & 0xFF, "02x") for b in u8_list)

def find_proofs_recursively(obj: dict) -> List[Dict]:
    """
    Walk nested JSON returned by the Sui object query and extract proof entries.
    We consider objects containing keys 'bundle_hash' 'fairness_score' 'timestamp' to be proofs.
    """
    proofs = []

    if not isinstance(obj, dict):
        return proofs

    # check if current object looks like a proof
    if all(k in obj for k in ("bundle_hash", "fairness_score", "timestamp")):
        proofs.append({
            "bundle_hash": obj["bundle_hash"],
            "fairness_score": obj["fairness_score"],
            "timestamp": obj["timestamp"]
        })

    # recurse into dict values
    for v in obj.values():
        if isinstance(v, dict):
            proofs.extend(find_proofs_recursively(v))
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    proofs.extend(find_proofs_recursively(item))
    return proofs


def read_audit_table() -> List[Dict]:
    """
    Query the Sui fullnode RPC for the AuditTable object and return a list of proofs.
    Uses the 'sui_getObject' RPC method with showContent to get nested object content.
    """
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "sui_getObject",
            "params": [SUI_TABLE_ID, {"showContent": True}]
        }

        resp = requests.post(SUI_RPC, json=payload, timeout=20)
        resp.raise_for_status()
        obj = resp.json()

        # navigate to the 'result' content depending on RPC shape
        # typical shape: { "jsonrpc":"2.0","result":{ ... }, "id":1 }
        result = obj.get("result") or obj

        # try to find object fields containing data
        # result might contain 'details' -> 'data' -> 'content' etc
        candidate = None
        if isinstance(result, dict):
            # Try common places
            for key in ("details", "result", "value"):
                if key in result:
                    candidate = result[key]
                    break
            if candidate is None:
                candidate = result

        # final attempt: dive into candidate
        if isinstance(candidate, dict) and "data" in candidate:
            candidate = candidate["data"]

        # Now recursively search for proofs
        proofs = find_proofs_recursively(candidate if isinstance(candidate, dict) else result)

        if not proofs:
            # graceful empty return instead of failing
            return []

        # normalize bundle_hash: if it's a list (vector<u8>) convert to hex
        for p in proofs:
            fh = p.get("bundle_hash")
            if isinstance(fh, list):
                p["bundle_hash"] = _to_hex_from_u8_list(fh)
            # attach the table id for clarity
            p["sui_object"] = SUI_TABLE_ID

        return proofs

    except requests.RequestException as e:
        raise RuntimeError(f"Sui RPC request failed: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to read Sui AuditTable: {e}")
