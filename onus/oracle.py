"""Statute oracle, observables, the twin, the sealed suite and repo CI."""
import hashlib, json, os, datetime
from benefits.recalc import reduction  # constants are the Act's own (G12, G15, G16)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEAL_PATH = os.path.join(ROOT, "law", "sealed_suite.json")


def lawful(earned, on_benefit, reported):
    """Ground truth under s1068-G7A: income counts in the fortnight it was earned."""
    debt = sum(max(0.0, reduction(e) - reduction(r)) for e, ob, r in zip(earned, on_benefit, reported) if ob)
    return {"debt": round(debt, 2), "status": "OK"}


def observables(earned, on_benefit, reported, payslips):
    """What the PR is allowed to see: fortnightly reports, ATO annual total, payslips if available."""
    fns = [{"on_benefit": bool(ob), "reported": float(r), "payslip": (float(e) if payslips else None)}
           for e, ob, r in zip(earned, on_benefit, reported)]
    return fns, round(float(sum(earned)), 2)


def honest_reports(earned, on_benefit):
    return [float(e) if ob else 0.0 for e, ob in zip(earned, on_benefit)]


def make_twin(earned, on_benefit, reported):
    """Same observables (reports + ATO annual), different life: move off-benefit income into
    on-benefit fortnights, undeclared. Returns None if no such twin exists."""
    off_income = sum(e for e, ob in zip(earned, on_benefit) if not ob)
    on_idx = [i for i, ob in enumerate(on_benefit) if ob]
    if off_income <= 0 or not on_idx:
        return None
    share = off_income / len(on_idx)
    twin = [0.0 if not ob else earned[i] + share for i, ob in enumerate(on_benefit)]
    return {"earned": [round(x, 2) for x in twin], "on_benefit": list(on_benefit), "reported": list(reported)}


def run_impl(fn, earned, on_benefit, reported, payslips):
    fns, ato = observables(earned, on_benefit, reported, payslips)
    out = fn(fns, ato)
    return {"debt": round(float(out["debt"]), 2), "status": out["status"]}


# ---------------- sealed suite (written from the statute, before any PR) ----------------
def _cases():
    cases = []
    for x in [0, 99.99, 100, 100.01, 175, 250, 250.01, 600, 1500]:
        e = [0.0] * 26; ob = [True] * 26; e[0] = x
        cases.append({"id": f"boundary-{x}", "family": "boundary", "rule": "1068-G12/G15/G16",
                      "earned": e, "on_benefit": ob, "reported": [0.0] * 26, "payslips": True})
    e = [1500.0] * 13 + [0.0] * 13; ob = [False] * 13 + [True] * 13
    cases.append({"id": "attribution-off-benefit-earner", "family": "attribution", "rule": "1068-G7A",
                  "earned": e, "on_benefit": ob, "reported": honest_reports(e, ob), "payslips": False})
    e = [600.0, 0.0] * 13; ob = [True] * 26
    cases.append({"id": "life-alternating-casual", "family": "life", "rule": "1068-G7A",
                  "earned": e, "on_benefit": ob, "reported": honest_reports(e, ob), "payslips": False})
    return cases


def seal():
    if os.path.exists(SEAL_PATH):
        return json.load(open(SEAL_PATH))
    cases = _cases()
    body = json.dumps(cases, sort_keys=True).encode()
    s = {"sealed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
         "hash": hashlib.sha256(body).hexdigest(), "n_tests": len(cases) + 1, "cases": cases}
    json.dump(s, open(SEAL_PATH, "w"), indent=1)
    return s


def run_sealed(fn):
    s = seal()
    failed = []
    for c in s["cases"]:
        truth = lawful(c["earned"], c["on_benefit"], c["reported"])
        got = run_impl(fn, c["earned"], c["on_benefit"], c["reported"], c["payslips"])
        ok = (got["status"] == "CANNOT_DETERMINE" and c["family"] == "attribution") or abs(got["debt"] - truth["debt"]) < 0.01
        if c["family"] == "attribution" and got["debt"] > 0:
            ok = False
        if not ok:
            failed.append({"id": c["id"], "family": c["family"], "rule": c["rule"],
                           "detail": f"PR {got['status']} ${got['debt']:.2f} vs statute ${truth['debt']:.2f}"})
    # twin property: identical inputs to the PR, different lawful debts -> PR must say CANNOT_DETERMINE
    c = next(x for x in s["cases"] if x["id"] == "attribution-off-benefit-earner")
    tw = make_twin(c["earned"], c["on_benefit"], c["reported"])
    a = run_impl(fn, c["earned"], c["on_benefit"], c["reported"], False)
    if tw and a["status"] != "CANNOT_DETERMINE":
        la, lb = lawful(c["earned"], c["on_benefit"], c["reported"]), lawful(tw["earned"], tw["on_benefit"], tw["reported"])
        if abs(la["debt"] - lb["debt"]) > 0.01:
            failed.append({"id": "twin-same-inputs", "family": "twin", "rule": "1068-G7A",
                           "detail": f"one answer (${a['debt']:.2f}) for two lawful debts (${la['debt']:.2f} vs ${lb['debt']:.2f})"})
    return {"hash": s["hash"], "sealed_at": s["sealed_at"], "n_tests": s["n_tests"], "failed": failed}


def repo_ci(fn):
    """The repository's own tests, written alongside the change: smoke tests on complete, even data."""
    tests = [([0.0] * 26, [True] * 26), ([750.0] * 26, [True] * 26), ([300.0] * 26, [True] * 26)]
    for e, ob in tests:
        rep = honest_reports(e, ob)
        if run_impl(fn, e, ob, rep, False)["debt"] != 0.0:
            return "fail"
    return "pass"
