# backend/services/explain.py
import os
import openai
from typing import Dict, Any

openai.api_key = os.getenv("OPENAI_API_KEY")

BASE_PROMPT = """
You are an expert ML auditor. Given the following fairness metrics for an ML model/dataset, produce:
1) A concise summary (2-3 sentences)
2) An explanation which groups are disadvantaged and why (3-4 sentences)
3) Two recommended mitigation steps (bulleted)
4) A confidence score (0-100)

Return JSON with keys: summary, analysis, recommendations, confidence.
Metrics: {metrics}
"""

def generate_explanation(metrics: Dict[str, Any]) -> Dict[str, str]:
    """
    Generate structured explanation using OpenAI. If OpenAI fails or is not available, return deterministic fallback.
    """
    try:
        prompt = BASE_PROMPT.format(metrics=metrics)
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}],
            temperature=0.2,
            max_tokens=450
        )
        raw = response["choices"][0]["message"]["content"]
        # Try to parse JSON out of raw - sometimes LLM returns plain text; here we do a very forgiving parse
        import json
        try:
            parsed = json.loads(raw)
            return parsed
        except Exception:
            # Fallback: wrap raw text into fields
            return {"summary": raw[:250], "analysis": raw, "recommendations": "See text", "confidence": "N/A"}
    except Exception as e:
        # Fallback deterministic explanation
        dp = metrics.get("demographic_parity_difference")
        if dp is None:
            return {"summary": "No fairness metric available", "analysis": "Metric computation failed", "recommendations": "Retry with valid dataset", "confidence": "0"}
        summary = f"Demographic parity difference = {dp:.4f}. Groups with lower selection rates are disadvantaged."
        recs = "- Reweight training examples\n- Remove / mask proxy features"
        return {"summary": summary, "analysis": summary, "recommendations": recs, "confidence": "50"}
