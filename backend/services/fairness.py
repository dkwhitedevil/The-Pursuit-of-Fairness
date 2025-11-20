# backend/services/fairness.py
import pandas as pd
import numpy as np
import platform
from sklearn.metrics import confusion_matrix
from typing import Dict, Any, List, Optional, Tuple

def _choose_positive_class(series: pd.Series):
    """Choose a reasonable positive class for binarization.

    - If series is binary 0/1, choose 1.
    - If series looks like probabilities (0-1 floats), return None to threshold later.
    - Otherwise pick the most frequent class.
    """
    if series.dropna().empty:
        return None
    if pd.api.types.is_numeric_dtype(series):
        unique = pd.unique(series.dropna())
        unique_set = set([float(u) for u in unique]) if len(unique) < 50 else None
        if unique_set is not None and unique_set <= {0.0, 1.0}:
            return 1
        # if probabilities between 0 and 1
        try:
            if series.dropna().between(0, 1).all():
                return None
        except Exception:
            pass
        return None
    # non-numeric: pick the most frequent value
    try:
        return series.mode().iloc[0]
    except Exception:
        return None

def _binarize_series(series: pd.Series, positive_class=None, threshold: float = 0.5):
    """Convert a series to binary 0/1 using heuristics.

    Returns a pandas Series of ints (0/1).
    """
    if series.dropna().empty:
        return series.astype(float).fillna(0).astype(int)
    if pd.api.types.is_numeric_dtype(series):
        unique = pd.unique(series.dropna())
        # explicit binary
        if len(unique) <= 2 and set([float(u) for u in unique]) <= {0.0, 1.0}:
            return series.astype(int)
        # probabilities
        try:
            if series.dropna().between(0, 1).all():
                return (series >= threshold).astype(int)
        except Exception:
            pass
        # fallback: compare to most frequent value
        if positive_class is None:
            try:
                pos = pd.Series(series).mode().iloc[0]
            except Exception:
                pos = None
        else:
            pos = positive_class
        if pos is None:
            # last resort: threshold at median
            med = float(series.dropna().median())
            return (series >= med).astype(int)
        return (series == pos).astype(int)
    else:
        pos = positive_class if positive_class is not None else series.mode().iloc[0]
        return (series == pos).astype(int)

def _safe_confusion(y_true, y_pred):
    labels = [0, 1]
    try:
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=labels).ravel()
    except Exception:
        # build confusion matrix robustly
        try:
            arr = confusion_matrix(y_true, y_pred, labels=np.unique(np.concatenate((y_true, y_pred))))
            # try to map to tn, fp, fn, tp if possible
            if arr.shape == (1, 1):
                val = int(arr[0, 0])
                if int(y_true.iloc[0]) == 0:
                    return {"tn": val, "fp": 0, "fn": 0, "tp": 0}
                else:
                    return {"tn": 0, "fp": 0, "fn": 0, "tp": val}
        except Exception:
            pass
        return {"tn": 0, "fp": 0, "fn": 0, "tp": 0}
    return {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}


def _compute_rates_from_confusion(cm: Dict[str, int]) -> Dict[str, Optional[float]]:
    tp = cm.get("tp", 0)
    tn = cm.get("tn", 0)
    fp = cm.get("fp", 0)
    fn = cm.get("fn", 0)
    tpr = tp / (tp + fn) if (tp + fn) > 0 else None
    fpr = fp / (fp + tn) if (fp + tn) > 0 else None
    return {"tpr": tpr, "fpr": fpr}

def _detect_label_column(df: pd.DataFrame) -> Tuple[Optional[str], str]:
    # common label names
    candidates = [c for c in df.columns if str(c).lower() in ("label", "target", "y", "y_true", "ground_truth", "true")]
    if candidates:
        return candidates[0], "name_match"
    # heuristics: last column if binary-like
    for c in [df.columns[-1], df.columns[0]]:
        ser = df[c]
        if ser.dropna().empty:
            continue
        if pd.api.types.is_numeric_dtype(ser):
            uniq = pd.unique(ser.dropna())
            if len(uniq) <= 2 or ser.dropna().between(0, 1).all():
                return c, "heuristic"
    return None, "not_found"

def _detect_y_pred_column(df: pd.DataFrame) -> Optional[str]:
    pred_names = ("y_pred", "pred", "prediction", "yhat", "score", "prob")
    for c in df.columns:
        if str(c).lower() in pred_names:
            return c
    # a column similar to label but with 'pred' in name
    for c in df.columns:
        if "pred" in str(c).lower() and c not in df.columns:
            return c
    return None


def _detect_protected_columns(df: pd.DataFrame, exclude: List[str] = None) -> List[str]:
    if exclude is None:
        exclude = []
    protected_candidates = []
    name_based = set(["gender", "sex", "race", "ethnicity", "age", "zipcode", "zip", "country", "region", "religion", "disability"])
    for c in df.columns:
        ln = str(c).lower()
        if c in exclude:
            continue
        if ln in name_based:
            protected_candidates.append(c)
            continue
        # low cardinality columns (categorical-like)
        try:
            nunique = df[c].nunique(dropna=True)
        except Exception:
            continue
        if nunique <= max(10, min(50, int(len(df) * 0.02))):
            protected_candidates.append(c)
    # remove duplicates and prefer name matches first
    if not protected_candidates:
        # fallback: first column that is not label
        for c in df.columns:
            if c not in exclude:
                protected_candidates.append(c)
                break
    # dedupe preserving order
    seen = set()
    out = []
    for c in protected_candidates:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def run_fairness_audit(df: pd.DataFrame) -> Dict[str, Any]:
    """Run a robust fairness audit with automatic detection.

    The function will try to detect label, prediction, and one or more protected columns.
    It computes selection rates, demographic parity difference, per-group confusion, TPR/FPR gaps,
    and returns a structured dict with metadata and warnings.
    """
    if df.shape[1] < 2:
        raise ValueError("Data must have at least 2 columns.")

    detected_label, label_reason = _detect_label_column(df)
    y_pred_col = _detect_y_pred_column(df)
    exclude = []
    if detected_label:
        exclude.append(detected_label)
    if y_pred_col:
        exclude.append(y_pred_col)

    protected_cols = _detect_protected_columns(df, exclude=exclude)

    # choose primary protected column
    primary_protected = protected_cols[0] if protected_cols else df.columns[0]

    # determine label and prediction series
    if detected_label:
        label_col = detected_label
    else:
        label_col = df.columns[-1]

    if y_pred_col:
        pred_col = y_pred_col
    else:
        # fallback to label (no explicit predictions)
        pred_col = label_col

    y_true_raw = df[label_col].copy()
    y_pred_raw = df[pred_col].copy()

    # decide whether task is binary classification, multiclass, or regression
    task_type = "binary"
    if pd.api.types.is_numeric_dtype(y_true_raw):
        uniq = pd.unique(y_true_raw.dropna())
        if len(uniq) > 50 and not y_true_raw.dropna().between(0, 1).all():
            task_type = "regression"
        elif len(uniq) > 2:
            task_type = "multiclass"
    else:
        if df[label_col].nunique() > 10:
            task_type = "regression"

    # binarize for binary tasks
    pos_label = _choose_positive_class(y_true_raw)
    y_true = _binarize_series(y_true_raw, positive_class=pos_label)
    y_pred = _binarize_series(y_pred_raw, positive_class=pos_label)

    def analyze_protected(col: str) -> Dict[str, Any]:
        series = df[col].astype(str).fillna("MISSING")
        groups = series.unique().tolist()
        selection_rates = {}
        per_group_confusion = {}
        per_group_rates = {}
        tpr_map = {}
        fpr_map = {}
        for g in groups:
            mask = series == str(g)
            if mask.sum() == 0:
                selection_rates[g] = None
                per_group_confusion[g] = None
                continue
            grp_y_true = y_true[mask]
            grp_y_pred = y_pred[mask]
            sel_rate = float(grp_y_pred.mean()) if len(grp_y_pred) > 0 else None
            selection_rates[g] = sel_rate
            cm = _safe_confusion(grp_y_true, grp_y_pred)
            per_group_confusion[g] = cm
            rates = _compute_rates_from_confusion(cm)
            per_group_rates[g] = rates
            tpr_map[g] = rates.get("tpr")
            fpr_map[g] = rates.get("fpr")

        valid_rates = [r for r in selection_rates.values() if r is not None]
        dp_diff = float(max(valid_rates) - min(valid_rates)) if valid_rates else None
        # Disparate impact ratio (min / max)
        di_ratio = None
        if valid_rates and min(valid_rates) > 0:
            di_ratio = float(min(valid_rates) / max(valid_rates)) if max(valid_rates) > 0 else None

        # TPR and FPR gaps
        tprs = [v for v in tpr_map.values() if v is not None]
        fprs = [v for v in fpr_map.values() if v is not None]
        tpr_gap = float(max(tprs) - min(tprs)) if tprs else None
        fpr_gap = float(max(fprs) - min(fprs)) if fprs else None

        return {
            "protected_column": col,
            "groups": groups,
            "selection_rate": selection_rates,
            "demographic_parity_difference": dp_diff,
            "disparate_impact_ratio": di_ratio,
            "per_group_confusion": per_group_confusion,
            "per_group_rates": per_group_rates,
            "tpr_gap": tpr_gap,
            "fpr_gap": fpr_gap,
        }

    analysis = []
    for col in protected_cols:
        analysis.append(analyze_protected(col))

    # derive a simple aggregate fairness score from primary protected attribute's DP diff
    primary_analysis = analysis[0] if analysis else analyze_protected(primary_protected)
    dp = primary_analysis.get("demographic_parity_difference")
    fairness_score = None
    if dp is not None:
        fairness_score = max(0.0, 100.0 - (abs(dp) * 100.0))

    result = {
        "detected_label": label_col,
        "label_detection_reason": label_reason,
        "detected_prediction": pred_col,
        "task_type": task_type,
        "protected_columns": protected_cols,
        "primary_protected": primary_protected,
        "analysis": analysis,
        "fairness_score": fairness_score,
        "python": platform.python_version(),
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
    }
    return result
