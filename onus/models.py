"""Sponsor model calls: SubQ Snap (decisions), Meta Muse (reads the Act), with timing for on-stage proof."""
import json, os, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _env():
    env = {}
    for p in [os.path.join(ROOT, ".env"), os.path.join(os.path.dirname(ROOT), ".env")]:
        if os.path.exists(p):
            for line in open(p):
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    env.setdefault(k, v)
    return env


ENV = _env()


def _post(url, headers, body, timeout=60):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    t = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode()), int((time.time() - t) * 1000)


TRIAGE = {
    "statute_defect": "The code contradicts the statute",
    "declared_policy_change": "An intended policy change that the PR description discloses",
    "oracle_doubt": "The statute oracle or test itself may be wrong",
    "statute_ambiguity": "The statute is genuinely ambiguous here; a lawyer must decide",
    "no_divergence": "No material divergence between PR and statute",
}
SEVERITY = ["cosmetic or none", "minor (under $10 per person)", "material (the letter amount changes)",
            "severe (a debt is raised where the law allows none)"]


def snap_decide(rules, pr, divergence):
    """One sub-second Snap request: clause map + disclosure + triage + severity."""
    state = {
        "statute_rules": [{"id": r["id"], "page": r["page"], "quote": r["quote"]} for r in rules],
        "pull_request": {"title": pr["title"], "description": pr["description"], "diff": pr["diff"]},
        "observed": divergence,
    }
    q = {f"clause_{r['id'].replace('-', '_')}": {
        "type": "noul", "instructions": f"Does the diff itself rewrite the logic that implements rule {r['id']} ({r.get('role','')})? "
                                         "Answer about the changed lines only, not about downstream effects on other rules' inputs.",
        "criteria": {"true": "The changed lines implement or alter this specific rule",
                     "false": "The changed lines do not implement this rule; at most its inputs change"}} for r in rules}
    q["disclosure"] = {"type": "noul", "instructions": "Does the PR description truthfully disclose the behaviour change the diff makes?",
                       "criteria": {"true": "The description states the behaviour change", "false": "The description says there is no behaviour change, or omits it"}}
    q["triage"] = {"type": "choice", "instructions": "Given the statute, the diff and the observed divergence, what is this?", "criteria": TRIAGE}
    q["severity"] = {"type": "score", "instructions": "How severe is the impact on a recipient?", "criteria": SEVERITY}
    resp, ms = _post("https://api.subq.ai/v1/systemone", {"Authorization": f"Bearer {ENV['SUBQ_API_KEY']}"},
                     {"model": "subq-snap-1.1", "state": state, "questions": q}, timeout=30)
    a = resp["answers"]
    clauses = [{"id": r["id"], "p": round(a[f"clause_{r['id'].replace('-', '_')}"]["noul"], 3)} for r in rules]
    tri = a["triage"]
    sev = a["severity"]
    diverges = divergence.get("diverges", False)
    if not diverges and tri["choice"] in ("no_divergence", "declared_policy_change"):
        route = "PASS"
    elif tri["choice"] == "statute_defect" and tri["confidence"] >= 0.7:
        route = "BLOCK"
    elif tri["choice"] in ("statute_ambiguity", "oracle_doubt") or tri["confidence"] < 0.7:
        route = "ASK"
    else:
        route = "BLOCK" if diverges else "PASS"
    return {"latency_ms": ms, "input_tokens": resp.get("usage", {}).get("input_tokens"), "clauses": clauses,
            "disclosure_p": round(a["disclosure"]["noul"], 3),
            "triage": {"choice": tri["choice"], "probabilities": {k: round(v, 3) for k, v in tri["probabilities"].items()},
                       "confidence": round(tri["confidence"], 3)},
            "severity": round(sev["score"], 2), "route": route}


def muse_ask(claim, rules, pages):
    """Muse Spark answers a judge's claim against the extracted rules + the cited pages of the Act."""
    ctx = "\n\n".join(f"=== PDF PAGE {p} ===\n{t}" for p, t in pages.items())
    rl = "\n".join(f"- {r['id']} (p.{r['page']}): {r['quote']}" for r in rules)
    prompt = (f"You are checking a claim against Australia's Social Security Act 1991 (vol. 3, compilation 147).\n"
              f"Extracted rules:\n{rl}\n\nPages of the Act:\n{ctx}\n\nCLAIM: {claim}\n\n"
              "Answer ONLY with JSON: {\"verdict\": \"CONFIRMED\"|\"REFUTED\"|\"NOT IN EVIDENCE\", \"rule_id\": ..., \"page\": <int>, "
              "\"quote\": <verbatim supporting text, <=200 chars>}. Use NOT IN EVIDENCE if these pages do not settle it.")
    resp, ms = _post("https://api.meta.ai/v1/chat/completions", {"Authorization": f"Bearer {ENV['META_API_KEY']}"},
                     {"model": "muse-spark-1.3", "max_tokens": 4000, "messages": [{"role": "user", "content": prompt}]}, timeout=60)
    txt = resp["choices"][0]["message"]["content"].strip()
    txt = txt[txt.find("{"): txt.rfind("}") + 1]
    out = json.loads(txt)
    out.update({"latency_ms": ms, "model": "muse-spark-1.3"})
    return out
