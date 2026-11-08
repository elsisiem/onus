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


ENV = {**_env(), **{k: v for k, v in os.environ.items() if k.endswith("_API_KEY")}}  # deploy secrets override .env


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
    """Two parallel sub-second Snap requests.
    A (blind): statute rules + PR title/description/diff ONLY -> clause map + disclosure. No oracle outputs.
    B (disclosed inputs): rules + PR + the sealed-suite outcome summary -> triage + severity."""
    import concurrent.futures as cf
    rules_state = [{"id": r["id"], "page": r["page"], "quote": r["quote"]} for r in rules]
    pr_state = {"title": pr["title"], "description": pr["description"], "diff": pr["diff"]}
    state = {"statute_rules": rules_state, "pull_request": pr_state}
    q = {f"clause_{r['id'].replace('-', '_')}": {
        "type": "noul", "instructions": f"Does the diff itself rewrite the logic that implements rule {r['id']} ({r.get('role','')})? "
                                         "Answer about the changed lines only, not about downstream effects on other rules' inputs.",
        "criteria": {"true": "The changed lines implement or alter this specific rule",
                     "false": "The changed lines do not implement this rule; at most its inputs change"}} for r in rules}
    q["disclosure"] = {"type": "noul", "instructions": "Does the PR description truthfully disclose the behaviour change the diff makes?",
                       "criteria": {"true": "The description states the behaviour change", "false": "The description says there is no behaviour change, or omits it"}}
    qb = {"triage": {"type": "choice", "instructions": "Given the statute, the diff and the sealed-suite outcome, what is this?", "criteria": TRIAGE},
          "severity": {"type": "score", "instructions": "How severe is the impact on a recipient?", "criteria": SEVERITY}}
    state_b = {**state, "sealed_suite_outcome": {"failed_families": divergence.get("sealed_failure_families", []),
                                                 "outputs_differ": divergence.get("diverges", False)}}
    hdr = {"Authorization": f"Bearer {ENV['SUBQ_API_KEY']}"}
    with cf.ThreadPoolExecutor(2) as ex:
        fa = ex.submit(_post, "https://api.subq.ai/v1/systemone", hdr, {"model": "subq-snap-1.1", "state": state, "questions": q}, 30)
        fb = ex.submit(_post, "https://api.subq.ai/v1/systemone", hdr, {"model": "subq-snap-1.1", "state": state_b, "questions": qb}, 30)
        (ra, ma), (rb, mb) = fa.result(), fb.result()
    a, b = ra["answers"], rb["answers"]
    clauses = [{"id": r["id"], "p": round(a[f"clause_{r['id'].replace('-', '_')}"]["noul"], 3)} for r in rules]
    tri, sev = b["triage"], b["severity"]
    return {"latency_ms": max(ma, mb), "latency_blind_ms": ma, "latency_triage_ms": mb,
            "input_tokens": (ra.get("usage", {}).get("input_tokens") or 0) + (rb.get("usage", {}).get("input_tokens") or 0),
            "clauses": clauses, "disclosure_p": round(a["disclosure"]["noul"], 3),
            "inputs": {"clause_map_and_disclosure": "statute rules + PR title/description/diff only (no oracle outputs)",
                       "triage_and_severity": "the above + sealed-suite failed families + whether outputs differ"},
            "triage": {"choice": tri["choice"], "probabilities": {k: round(v, 3) for k, v in tri["probabilities"].items()},
                       "confidence": round(tri["confidence"], 3)},
            "severity": round(sev["score"], 2)}


def muse_ask(claim, rules, pages):
    """Muse Spark answers a judge's claim against the extracted rules + the cited pages of the Act."""
    # Stage speed: the rules' quotes are already verified verbatim against the Act text, so they are the context (~4 s).
    rl = "\n".join(f"- {r['id']} (p.{r['page']}): {r['quote']}" for r in rules)
    prompt = (f"You are checking a claim against Australia's Social Security Act 1991 (vol. 3, compilation 147).\n"
              f"Rules extracted from the Act, each quote verified verbatim against the text:\n{rl}\n\nCLAIM: {claim}\n\n"
              "Answer ONLY with JSON: {\"verdict\": \"CONFIRMED\"|\"REFUTED\"|\"NOT IN EVIDENCE\", \"rule_id\": ..., \"page\": <int>, "
              "\"quote\": <verbatim supporting text, <=200 chars>}. Use NOT IN EVIDENCE if these pages do not settle it.")
    resp, ms = _post("https://api.meta.ai/v1/chat/completions", {"Authorization": f"Bearer {ENV['META_API_KEY']}"},
                     {"model": "muse-spark-1.3", "max_tokens": 4000, "messages": [{"role": "user", "content": prompt}]}, timeout=60)
    txt = resp["choices"][0]["message"]["content"].strip()
    txt = txt[txt.find("{"): txt.rfind("}") + 1]
    out = json.loads(txt)
    out.update({"latency_ms": ms, "model": "muse-spark-1.3"})
    return out
