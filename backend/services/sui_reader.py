import json
import subprocess
from typing import List, Dict

SUI_TABLE_ID = "0x3f65bc27fd881f1d1f9ebea9d2c30cbce9f6c981dd691a2b545b5180df94841d"

def find_proofs_recursively(obj: dict) -> List[Dict]:
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
    try:
        cmd = ["sui", "client", "object", SUI_TABLE_ID, "--json"]
        output = subprocess.check_output(cmd, text=True)
        obj = json.loads(output)

        proofs = find_proofs_recursively(obj)

        if not proofs:
            raise RuntimeError("No proofs found in Sui AuditTable object")

        # normalize bundle_hash if it’s a list of ints
        for p in proofs:
            fh = p["bundle_hash"]
            if isinstance(fh, list):
                p["bundle_hash"] = "".join(format(int(b), "02x") for b in fh)
            p["sui_object"] = SUI_TABLE_ID

        return proofs

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"sui client failed: {e.stderr or e.output or str(e)}")
    except Exception as e:
        raise RuntimeError(f"Failed to read Sui AuditTable: {e}")
