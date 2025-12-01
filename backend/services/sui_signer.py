import subprocess
import json

def anchor_audit(blob_id: str, score: int):
    result = subprocess.run(
        ["node", "services/sui_anchor.mjs", blob_id, str(score)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        return {"status": "error", "stderr": result.stderr}

    try:
        res_json = json.loads(result.stdout)
        digest = res_json.get("digest")
        return {
            "status": "success",
            "digest": digest,
            "explorer": f"https://suiexplorer.com/txblock/{digest}?network=testnet",
            "raw": res_json
        }
    except Exception:
        return {"status": "error", "output": result.stdout}
