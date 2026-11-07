"""ONUS demo server: python3 server.py  ->  http://127.0.0.1:8787"""
import hashlib, json, os, sys, datetime, traceback
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from onus import law, oracle, models  # noqa: E402
from prs import PRS  # noqa: E402

RULES = law.load_rules()
LAST = {}


def run(body):
    earned = [max(0.0, float(x)) for x in body["earned"]][:26]
    on_benefit = [bool(x) for x in body["on_benefit"]][:26]
    payslips = bool(body.get("payslips", False))
    key = body.get("pr", "averaging")
    pr = PRS[key]
    reported = oracle.honest_reports(earned, on_benefit)
    truth = oracle.lawful(earned, on_benefit, reported)
    got = oracle.run_impl(pr["fn"], earned, on_benefit, reported, payslips)
    twin = oracle.make_twin(earned, on_benefit, reported)
    twin_out = None
    if twin:
        twin_out = {**twin, "lawful": oracle.lawful(twin["earned"], twin["on_benefit"], twin["reported"]),
                    "pr": oracle.run_impl(pr["fn"], twin["earned"], twin["on_benefit"], twin["reported"], False),
                    "same_inputs_to_pr": True}
        twin_out["explanation"] = (f"Same reports and same ATO annual income (${sum(earned):,.2f}). "
                                   f"Lawful debt: ${twin_out['lawful']['debt']:,.2f} for the twin, ${truth['debt']:,.2f} for this person. "
                                   "Without payslips, any answer computed from these inputs is wrong for at least one of them.")
    sealed = oracle.run_sealed(pr["fn"])
    diverges = (got["status"] != truth["status"] and not (got["status"] == "CANNOT_DETERMINE")) or abs(got["debt"] - truth["debt"]) > 0.005 or bool(sealed["failed"])
    divergence = {"diverges": diverges, "persona": {"annual_income": round(sum(earned), 2), "fortnights_on_benefit": sum(on_benefit),
                  "payslips_available": payslips}, "lawful_debt": truth["debt"], "pr_debt": got["debt"], "pr_status": got["status"],
                  "sealed_failure_families": sorted({f["family"] for f in sealed["failed"]})}
    try:
        snap = models.snap_decide(RULES, pr, divergence)
    except Exception as e:  # never fake a decision
        snap = {"error": f"SubQ unavailable: {e}", "route": "ASK", "clauses": [], "triage": {}, "latency_ms": None}
    route = snap["route"]
    top = max(snap.get("clauses") or [{"id": pr["misreads"] or "-", "p": 0}], key=lambda c: c["p"])
    rule = next((r for r in RULES if r["id"] == (pr["misreads"] or top["id"])), None)
    headline = {"BLOCK": f"BLOCKED — {pr['misreads'] or top['id']}", "PASS": "PASS — matches the Act", "ASK": "ASK A LAWYER"}[route]
    out = {"lawful": truth, "pr": {"id": key, **got, "misreads": pr["misreads"], "description": pr["description"], "title": pr["title"]},
           "letter": {"would_send": got["status"] == "OK" and got["debt"] > 0, "amount": got["debt"], "lawful_amount": truth["debt"]},
           "twin": twin_out, "sealed": sealed, "snap": snap,
           "verdict": {"route": route, "headline": headline, "clause": rule["id"] if rule else None, "page": rule["page"] if rule else None}}
    LAST.clear(); LAST.update({"request": body, "result": out})
    return out


def redteam():
    rows = []
    for key in ["averaging", "free_area", "cliff"]:
        pr = PRS[key]
        sealed = oracle.run_sealed(pr["fn"])
        rows.append({"id": key, "misreads": pr["misreads"], "description": pr["fn"].__doc__.strip().split("\n")[0],
                     "repo_ci": oracle.repo_ci(pr["fn"]), "onus": "BLOCK" if sealed["failed"] else "PASS",
                     "failed_families": sorted({f["family"] for f in sealed["failed"]})})
    return {"k": len(rows), "repo_ci_caught": sum(r["repo_ci"] == "fail" for r in rows),
            "onus_caught": sum(r["onus"] == "BLOCK" for r in rows), "mutants": rows}


def cert():
    res = LAST.get("result") or run({"earned": [1500.0] * 13 + [0.0] * 13, "on_benefit": [False] * 13 + [True] * 13, "pr": "averaging"})
    pr_src = open(os.path.join(ROOT, "prs", "__init__.py"), "rb").read()
    st = {"_type": "https://in-toto.io/Statement/v1",
          "subject": [{"name": f"prs/{res['pr']['id']}", "digest": {"sha256": hashlib.sha256(pr_src).hexdigest()}}],
          "predicateType": "https://onus.dev/statute-conformance/v0.1",
          "predicate": {"verifier": {"id": "onus", "models": {"reader": "muse-spark-1.3", "decider": "subq-snap-1.1", "red_team": "gemini-3.8-flash"}},
                        "statute": law.ACT, "rules": [{k: r[k] for k in ("id", "page", "verified")} for r in RULES],
                        "sealed_suite": {k: res["sealed"][k] for k in ("hash", "sealed_at", "n_tests")},
                        "result": {"route": res["verdict"]["route"], "failed": res["sealed"]["failed"], "lawful_debt": res["lawful"]["debt"],
                                   "pr_debt": res["pr"]["debt"]},
                        "decisions": {k: res["snap"].get(k) for k in ("clauses", "disclosure_p", "triage", "severity", "route", "latency_ms")},
                        "timeVerified": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                        "scope": "Illustrative single-adult Newstart income test; synthetic people and PRs; real statute text. Not legal advice."}}
    body = json.dumps(st, sort_keys=True).encode()
    return {"statement": st, "sha256": hashlib.sha256(body).hexdigest()}


class H(BaseHTTPRequestHandler):
    def _send(self, code, obj, ctype="application/json"):
        data = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(data)

    def log_message(self, fmt, *a):
        sys.stderr.write("[onus] " + (fmt % a) + "\n")

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            return self._send(200, open(os.path.join(ROOT, "ui", "index.html"), "rb").read(), "text/html; charset=utf-8")
        if self.path == "/api/rules":
            return self._send(200, {"act": law.ACT, "rules": RULES})
        self._send(404, {"error": "not found"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        try:
            if self.path == "/api/run":
                return self._send(200, run(body))
            if self.path == "/api/redteam":
                return self._send(200, redteam())
            if self.path == "/api/cert":
                return self._send(200, cert())
            if self.path == "/api/ask":
                pages = law.page_text(sorted({r["page"] for r in RULES}))
                return self._send(200, models.muse_ask(body.get("claim", ""), RULES, pages))
            self._send(404, {"error": "not found"})
        except Exception as e:
            traceback.print_exc()
            self._send(500, {"error": str(e)})


if __name__ == "__main__":
    oracle.seal()
    port = int(os.environ.get("PORT", "8787"))
    print(f"ONUS on http://127.0.0.1:{port}  ({len(RULES)} rules, {sum(r['verified'] for r in RULES)} verified)")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
