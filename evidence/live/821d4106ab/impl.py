"""Simplified benefits engine: Newstart overpayment recalculation (single adult).

This module implements a simplified single-threshold, single-taper-rate income test
so caseworkers can easily calculate benefit reductions mentally.

Each fortnight dict has keys: on_benefit (bool), reported (float), payslip (float | None).
"""
THRESHOLD = 100.0
FREE_AREA = 100.0
TAPER_RATE = 0.5


def reduction(income):
    excess = max(0.0, income - THRESHOLD)
    return round(excess * TAPER_RATE, 2)


def recalculate_debt(fortnights, ato_annual_income=None):
    debt = 0.0
    for f in fortnights:
        if not f["on_benefit"]:
            continue
        actual = f["payslip"] if f.get("payslip") is not None else f["reported"]
        debt += max(0.0, reduction(actual) - reduction(f["reported"]))
    debt = round(debt, 2)
    if ato_annual_income is None:
        return {"debt": debt, "status": "OK"}
    evidenced = sum((f["payslip"] if f.get("payslip") is not None else f["reported"]) for f in fortnights)
    if ato_annual_income > evidenced + 0.005 and not all(f.get("payslip") is not None for f in fortnights):
        return {"debt": debt, "status": "CANNOT_DETERMINE"}
    return {"debt": debt, "status": "OK"}
