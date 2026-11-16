"""Route fictional support questions to reviewed guidance without an AI model."""

from datetime import date
from pathlib import Path
import argparse
import json
import re
import tempfile

from app import articles, initialise

ROOT = Path(__file__).resolve().parent
SECRET_PATTERN = re.compile(r"\b(?:password|token|secret)\s*[:=]\s*\S+", re.IGNORECASE)


def load_guidance(database, policy):
    """Combine existing knowledge articles with explicit fictional review metadata."""
    return [
        {**article, **policy[article["id"]]}
        for article in articles(database)
        if article["id"] in policy
    ]


def answer(question, guidance, as_of="2026-11-16"):
    """Return a cited guide, ask for clarification, or prepare a human handover."""
    if not isinstance(question, str) or len(question) > 500:
        raise ValueError("Use a support question of at most 500 characters")
    cutoff = date.fromisoformat(as_of)
    result = {
        "synthetic": True,
        "engine": "deterministic keyword routing",
        "cloud_calls": 0,
        "sources": [],
        "actions_executed": [],
    }
    if SECRET_PATTERN.search(question):
        return {
            **result,
            "decision": "redaction_required",
            "message": "Remove credentials before describing the issue. Never share passwords or tokens.",
            "handover": None,
        }
    query = " ".join(question.split())
    if not query:
        return {
            **result,
            "decision": "clarification",
            "message": "Which service is affected, and what error do you see?",
            "handover": None,
        }
    tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
    matches = [
        guide for guide in guidance
        if guide["status"] == "approved"
        and date.fromisoformat(guide["review_due"]) >= cutoff
        and tokens.intersection(guide["keywords"])
    ]
    if len(matches) > 1:
        return {
            **result,
            "decision": "clarification",
            "message": "Please describe one issue at a time: connection, application, or account access.",
            "handover": None,
        }
    if not matches:
        return {
            **result,
            "decision": "escalation",
            "message": "No current approved guide matches. Ask the support team to review the issue.",
            "handover": {
                "symptom": query,
                "service": "To be confirmed",
                "error_and_time": "Ask the user",
                "checks_completed": "No automated remediation performed",
                "next_owner": "Support triage",
            },
        }
    guide = matches[0]
    return {
        **result,
        "decision": "guidance",
        "message": guide["body"],
        "sources": [{
            "id": guide["id"],
            "title": guide["title"],
            "owner": guide["owner"],
            "review_due": guide["review_due"],
        }],
        "handover": None,
    }


def evaluate(guidance, cases, as_of="2026-11-16"):
    results = []
    for case in cases:
        response = answer(case["question"], guidance, as_of)
        actual_source = response["sources"][0]["id"] if response["sources"] else None
        matches = (
            response["decision"] == case["expected_decision"]
            and actual_source == case["expected_source"]
        )
        results.append({
            "id": case["id"],
            "expected_decision": case["expected_decision"],
            "actual_decision": response["decision"],
            "expected_source": case["expected_source"],
            "actual_source": actual_source,
            "matched": matches,
        })
    correct = sum(result["matched"] for result in results)
    return {
        "synthetic": True,
        "engine": "deterministic keyword routing",
        "as_of": as_of,
        "cases": len(results),
        "matched": correct,
        "fixture_match_rate": correct / len(results) if results else None,
        "cloud_calls": 0,
        "scope": "Labelled fictional questions; no real adoption, AI or service-performance result.",
        "results": results,
    }


def demo_guidance():
    policy = json.loads((ROOT / "examples/selfservice-policy.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as temporary:
        database = Path(temporary) / "knowledge.sqlite3"
        initialise(database)
        return load_guidance(database, policy)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question", default="")
    parser.add_argument("--evaluate", action="store_true")
    parser.add_argument("--as-of", default="2026-11-16")
    options = parser.parse_args()
    guidance = demo_guidance()
    if options.evaluate:
        cases = json.loads((ROOT / "examples/selfservice-queries.json").read_text(encoding="utf-8"))
        result = evaluate(guidance, cases, options.as_of)
        destination = ROOT / "reports/selfservice-evaluation.json"
        destination.parent.mkdir(exist_ok=True)
        destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    else:
        result = answer(options.question, guidance, options.as_of)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
