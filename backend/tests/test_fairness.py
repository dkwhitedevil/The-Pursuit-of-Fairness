import pandas as pd
from services.fairness import run_fairness_audit

def test_fairness_basic():
    df = pd.DataFrame({
        "protected": ["A","A","B","B","B","A"],
        "label": [1,0,1,0,1,1]
    })
    res = run_fairness_audit(df)
    assert "demographic_parity_difference" in res
    assert "selection_rate" in res
