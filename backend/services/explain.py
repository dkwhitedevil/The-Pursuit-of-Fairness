# backend/services/explain.py

import requests
import json
from typing import Dict, Any


# ---------------------------------------------------------
# Helper: Extract JSON from messy LLM output
# ---------------------------------------------------------
def extract_json(text: str):
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except:
        return None


# ---------------------------------------------------------
# SAFE METRIC COMPRESSION — critical for small LLMs
# ---------------------------------------------------------
def compress_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Reduce massive metrics blob into a tiny summary that small models can handle."""

    summary = {
        "fairness_score": metrics.get("fairness_score"),
        "primary_protected": metrics.get("primary_protected"),
        "top_violations": []
    }

    analysis = metrics.get("analysis", [])

    # pick top 3 worst columns by demographic parity difference
    sorted_cols = sorted(
        analysis,
        key=lambda x: abs(x.get("demographic_parity_difference", 0)),
        reverse=True
    )

    for col in sorted_cols[:3]:
        summary["top_violations"].append({
            "protected_column": col.get("protected_column"),
            "dpd": col.get("demographic_parity_difference"),
            "dir": col.get("disparate_impact_ratio")
        })

    return summary


# ---------------------------------------------------------
# MAIN FUNCTION
# ---------------------------------------------------------
def generate_explanation(metrics: Dict[str, Any]) -> Dict[str, Any]:
    try:
        safe = compress_metrics(metrics)

        prompt = f"""
You are an expert ML fairness auditor. You MUST return only VALID JSON.

Summaries must be short, precise, and NON-repetitive.

Return JSON with this structure:
{{
  "summary": "2–4 sentence summary of fairness",
  "analysis": "3–8 sentence deeper explanation",
  "recommendations": ["step 1", "step 2"],
  "confidence": 0-100
}}

Metrics summary to analyze: {safe}
"""

        # Call local model
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "qwen2.5:0.5b",
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            },
            stream=True,
            timeout=40
        )

        # Collect streamed tokens
        raw_text = ""
        for line in response.iter_lines():
            if not line:
                continue

            try:
                obj = json.loads(line.decode("utf-8"))
            except:
                continue

            if obj.get("done"):
                break

            if "message" in obj and "content" in obj["message"]:
                raw_text += obj["message"]["content"]

        # Try strict JSON parse
        parsed = extract_json(raw_text)
        if parsed:
            return parsed

        # fallback if JSON not found
        return {
            "summary": raw_text[:200],
            "analysis": raw_text,
            "recommendations": ["Refer to raw text"],
            "confidence": 40
        }

    except Exception as e:
        # final safety fallback with real metrics
        dp = metrics.get("fairness_score")
        summary = f"Fairness score = {dp}. Automated explanation unavailable due to model error."

        return {
            "summary": summary,
            "analysis": summary,
            "recommendations": ["Retry once server stabilizes", "Reduce model load"],
            "confidence": 30
        }
