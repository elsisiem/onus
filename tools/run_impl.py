"""Isolated runner: load an AI-written impl.py and evaluate it on cases read from stdin. Prints JSON."""
import importlib.util, json, sys

spec = importlib.util.spec_from_file_location("impl", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
out = {}
for c in json.load(sys.stdin):
    try:
        r = mod.recalculate_debt(c["fortnights"], c["ato_annual_income"])
        out[c["id"]] = {"debt": round(float(r["debt"]), 2), "status": str(r["status"])}
    except Exception as e:
        out[c["id"]] = {"error": f"{type(e).__name__}: {e}"[:160]}
print(json.dumps(out))
