"""Classifies a turn into skills + model tier via keyword matching — no
second LLM call, no extra cost. Mechanism only, OFF by default: flipping it
on needs the eval harness to confirm no quality regression, which costs
real API credits. With it off, agent.py behaves exactly as before this existed.
"""
import re

ENABLE_TURN_TRIAGE = False

SKILL_PATTERNS = {
    "planning": re.compile(r"\b(plan|schedule|week|next \d+ days?)\b", re.I),
    "workout": re.compile(r"\b(indoor|trainer|workout|watts?|ftp|gym|exercise)\b", re.I),
    "injury": re.compile(r"\b(pain|hurt|injur|sore|strain|knee|wrist)\b", re.I),
    "analysis": re.compile(r"\b(trend|progress|vo2max|how (am|have) i)\b", re.I),
}

# same model on both tiers until evals prove a cheaper one is safe — already
# hit Haiku 4.5's ceiling once (date arithmetic, anti-fabrication), don't
# repoint "simple" without re-running evals first
MODEL_TIERS = {"simple": "claude-sonnet-5", "default": "claude-sonnet-5"}


def classify_turn(user_message):
    """message -> {"skills": [...], "model_tier": "..."}. pure, no DB, no API call."""
    text = user_message or ""
    matched = [name for name, pattern in SKILL_PATTERNS.items() if pattern.search(text)]
    return {"skills": matched, "model_tier": "simple" if not matched else "default"}
