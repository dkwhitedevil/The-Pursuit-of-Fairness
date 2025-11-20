"""Sui client helpers for anchoring audit proofs.

This module provides a pragmatic, configurable anchor function that:
- Constructs a proof object (blob_hash, fairness_score, timestamp)
- Computes a deterministic `proof_hash` (SHA-256)
- If `SUI_RELAYER_URL` is set, POSTs the proof to that relayer and returns the relayer response
- Otherwise returns a simulated transaction receipt so the rest of the pipeline can operate

If you have a signing/relayer infra, set `SUI_RELAYER_URL` to an endpoint that accepts JSON
payloads and performs the on-chain submission (recommended for production).
"""
import os
import time
import json
import hashlib
from typing import Any, Dict
import logging

import requests

logger = logging.getLogger(__name__)


def _compute_proof_hash(proof: Dict[str, Any]) -> str:
    raw = json.dumps(proof, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def anchor_audit_on_sui(blob_hash: str, fairness_score) -> Dict[str, Any]:
    """Anchor an audit proof to Sui (via relayer) or return a simulated receipt.

    Parameters
    - blob_hash: content-addressed hash of the Walrus bundle
    - fairness_score: numeric fairness score or None

    Returns a dict with keys like `tx_digest`, `status`, `proof_hash`, and `relayer_response` (if used).
    """
    if not blob_hash:
        return {"error": "no_blob_hash"}

    proof = {
        "blob_hash": blob_hash,
        "fairness_score": fairness_score,
        "timestamp": int(time.time()),
    }
    proof_hash = _compute_proof_hash(proof)
    proof["proof_hash"] = proof_hash

    # If a relayer URL is configured, POST the proof to it and return its response
    relayer = os.getenv("SUI_RELAYER_URL")
    if relayer:
        try:
            headers = {"Content-Type": "application/json"}
            resp = requests.post(relayer, json=proof, headers=headers, timeout=15)
            try:
                body = resp.json()
            except Exception:
                body = {"text": resp.text}
            return {
                "tx_digest": body.get("tx_digest") or body.get("tx") or f"relayer_response_{proof_hash[:8]}",
                "status": "submitted",
                "proof_hash": proof_hash,
                "relayer_response": body,
                "relayer_status_code": resp.status_code,
            }
        except Exception as e:
            logger.exception("Failed to POST proof to SUI_RELAYER_URL")
            # fallthrough to simulated receipt

    # Fallback: return a simulated transaction digest and include the proof for external verification
    simulated_tx = f"simulated_sui_tx_{proof_hash[:12]}"
    explorer_template = os.getenv("SUI_EXPLORER_URL_TEMPLATE", "https://explorer.sui.io/tx/{tx}")
    explorer_url = explorer_template.format(tx=simulated_tx)
    return {
        "tx_digest": simulated_tx,
        "status": "simulated",
        "proof_hash": proof_hash,
        "explorer_url": explorer_url,
        "proof": proof,
    }


def verify_on_chain_proof(tx_digest: str, proof_hash: str) -> Dict[str, Any]:
    """Best-effort verification helper.

    If `SUI_RELAYER_URL` provided and supports verification, it may return verification details.
    Otherwise this returns a simulated verification status.
    """
    relayer = os.getenv("SUI_RELAYER_URL")
    if relayer:
        try:
            # Assume relayer exposes a GET /verify?tx=... or POST /verify; try GET first
            verify_url = relayer.rstrip("/") + "/verify"
            resp = requests.get(verify_url, params={"tx": tx_digest, "proof_hash": proof_hash}, timeout=10)
            try:
                return {"verified": resp.json().get("verified", False), "relayer_response": resp.json()}
            except Exception:
                return {"verified": resp.status_code == 200, "relayer_text": resp.text}
        except Exception:
            logger.exception("Relayer verification call failed")

    # Default simulated verification: match proof_hash prefix with tx_digest
    simulated_ok = tx_digest.endswith(proof_hash[:12])
    return {"verified": simulated_ok, "method": "simulated"}


__all__ = ["anchor_audit_on_sui", "verify_on_chain_proof"]
