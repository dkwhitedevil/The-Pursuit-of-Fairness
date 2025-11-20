import os
import json
import sys
from unittest import mock

import pytest
import time

# Ensure backend/ is on sys.path so `services` package can be imported
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from services.sui_client import anchor_audit_on_sui, _compute_proof_hash


def test_compute_proof_hash_consistency():
    proof = {"blob_hash": "abc123", "fairness_score": 90, "timestamp": 1600000000}
    h1 = _compute_proof_hash(proof)
    # compute again to ensure deterministic
    h2 = _compute_proof_hash(proof)
    assert h1 == h2
    assert isinstance(h1, str) and len(h1) == 64


def test_anchor_fallback_simulated(tmp_path, monkeypatch):
    # Ensure env has no relayer
    monkeypatch.delenv("SUI_RELAYER_URL", raising=False)
    res = anchor_audit_on_sui("walrus://deadbeef", 75)
    assert "proof_hash" in res
    assert res["status"] == "simulated"
    assert res["tx_digest"].startswith("simulated_sui_tx_")
    # proof is included
    assert isinstance(res.get("proof"), dict)
    assert res["proof"]["blob_hash"] == "walrus://deadbeef"


def test_anchor_uses_relayer(monkeypatch):
    # Patch requests.post to simulate relayer
    class FakeResp:
        def __init__(self, status_code=200, json_body=None, text=""):
            self.status_code = status_code
            self._json = json_body or {"tx_digest": "onchain_tx_12345"}
            self.text = text

        def json(self):
            return self._json

    def fake_post(url, json=None, headers=None, timeout=None):
        return FakeResp(200, {"tx_digest": "relayer_tx_abcdef"})

    monkeypatch.setenv("SUI_RELAYER_URL", "http://fake-relayer.local/submit")
    with mock.patch("services.sui_client.requests.post", side_effect=fake_post):
        res = anchor_audit_on_sui("walrus://feedface", 88)
        assert res["status"] == "submitted"
        assert "relayer_response" in res
        assert res["tx_digest"] == "relayer_tx_abcdef"


def test_proof_hashes_for_example_bundle(monkeypatch):
    """Verify the proof_hash computation and simulated tx digest match the provided bundle values.

    This uses the exact timestamps and fairness_score values from the user's example bundle
    so the deterministic SHA-256 proof_hash should match the canonical values.
    """
    # fix time to the example timestamp
    example_ts = 1763556503
    monkeypatch.setattr(time, "time", lambda: example_ts)

    # First proof (walrus blob + fairness_score)
    blob_a = "ebdb33c8a2f9a04003bfc430624b63f79f17cebd4a03d8c26f1336a03649c4e9"
    fairness_a = 88.22691975841241
    proof_a = {"blob_hash": blob_a, "fairness_score": fairness_a, "timestamp": example_ts}
    expected_hash_a = "9ec4fd618f7c6855d6c106cfe0c362015321746df036b42de9d81759e1319604"
    h_a = _compute_proof_hash(proof_a)
    assert h_a == expected_hash_a

    # Anchor and check simulated tx digest and explorer_url
    monkeypatch.delenv("SUI_RELAYER_URL", raising=False)
    res = anchor_audit_on_sui(blob_a, fairness_a)
    assert res["status"] == "simulated"
    assert res["proof_hash"] == expected_hash_a
    assert res["tx_digest"] == f"simulated_sui_tx_{expected_hash_a[:12]}"

    # Second proof (manifest blob, fairness_score was null in bundle)
    blob_b = "6bf9264d3ac859afa60cb1ce1150ae0953aa9ab26c8cd10cf95d6f7d6f400a87"
    fairness_b = None
    proof_b = {"blob_hash": blob_b, "fairness_score": fairness_b, "timestamp": example_ts}
    expected_hash_b = "73906bd69d868a2be86ccf7504afd4f1b19870c6b5690367a321c6ea99256e1d"
    h_b = _compute_proof_hash(proof_b)
    assert h_b == expected_hash_b

    res_b = anchor_audit_on_sui(blob_b, fairness_b)
    assert res_b["status"] == "simulated"
    assert res_b["proof_hash"] == expected_hash_b
    assert res_b["tx_digest"] == f"simulated_sui_tx_{expected_hash_b[:12]}"


if __name__ == "__main__":
    pytest.main(["-q"])
