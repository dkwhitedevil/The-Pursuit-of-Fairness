import json
from sui_client import anchor_audit_on_sui

if __name__ == "__main__":
    # Sample bundle and score
    sample_bundle = {"test": "real_anchor", "timestamp": "2025-11-21"}
    fairness_score = 99.99
    result = anchor_audit_on_sui(sample_bundle, fairness_score)
    print("SUI Anchor Test Result:")
    print(json.dumps(result, indent=2))
