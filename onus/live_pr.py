"""A real AI-written PR, generated live: Gemini implements a ticket against the legacy engine AND writes its own
unit tests (the implementer's CI). Both run in an isolated subprocess; then ONUS runs its sealed statute suite.
Nothing here is planted: the code and the tests are whatever the model writes, saved under runs/live/<id>/."""
import json, os, subprocess, sys, time, hashlib, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = os.path.join(ROOT, "evidence", "live")
RUNNER = os.path.join(ROOT, "tools", "run_impl.py")

TICKETS = {
    "BEN-412": open(os.path.join(ROOT, "law", "BEN-412-ticket.md")).read(),
    "BEN-430": ("# BEN-430: Simplify the income test\n\nProduct wants the income test to be easier to explain: replace the two-band reduction with "
                "a single threshold and a single taper rate so caseworkers can do it in their head. Keep the signature. Add unit tests."),
}


def _gemini(prompt, key, model="gemini-3.8-flash", timeout=90):
    body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}}
    req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                 data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": key})
    t = time.time()
    r = json.load(urllib.request.urlopen(req, timeout=timeout))
    txt = r["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(txt), int((time.time() - t) * 1000)


def generate(ticket_id, key):
    legacy = open(os.path.join(ROOT, "benefits", "recalc.py")).read()
    prompt = (f"You are a software engineer on a government benefits engine. Implement this ticket.\n\nTICKET:\n{TICKETS[ticket_id]}\n\n"
              f"CURRENT MODULE (benefits/recalc.py):\n```python\n{legacy}\n```\n\n"
              "Return JSON with keys: \"code\" (the complete new module, standard library only, keeping the function "
              "recalculate_debt(fortnights, ato_annual_income=None) -> {'debt': float, 'status': str}), \"tests\" (a complete "
              "unittest module that does `from impl import recalculate_debt` and tests your change), and \"description\" "
              "(the PR description). Each fortnight is a dict with keys on_benefit (bool), reported (float), payslip (float or None).")
    out, ms = _gemini(prompt, key)
    pid = hashlib.sha256((ticket_id + out["code"]).encode()).hexdigest()[:10]
    d = os.path.join(LIVE, pid); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "impl.py"), "w").write(out["code"])
    open(os.path.join(d, "test_impl.py"), "w").write(out["tests"])
    json.dump({"ticket": ticket_id, "description": out.get("description", ""), "gemini_ms": ms,
               "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}, open(os.path.join(d, "meta.json"), "w"), indent=1)
    return pid, d, out, ms


def run_own_tests(d):
    p = subprocess.run([sys.executable, "-E", "-m", "unittest", "-q", "test_impl"], cwd=d, capture_output=True, text=True, timeout=20)
    tail = (p.stderr or p.stdout).strip().splitlines()[-1:] or [""]
    return {"status": "pass" if p.returncode == 0 else "fail", "summary": tail[0][:160]}


def run_cases(d, cases):
    """Run the model's code on sealed cases in a subprocess; returns {case_id: {debt, status}|{error}}."""
    p = subprocess.run([sys.executable, "-I", RUNNER, os.path.join(d, "impl.py")], input=json.dumps(cases),
                       capture_output=True, text=True, timeout=20)
    return json.loads(p.stdout or "{}")
