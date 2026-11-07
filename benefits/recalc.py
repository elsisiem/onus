"""Legacy benefits engine: Newstart overpayment recalculation (single adult, illustrative).

This is the repository under change. Its behaviour follows the statute:
income is assessed in the fortnight it is earned (s1068-G7A). An ATO annual
figure is never apportioned across fortnights; if it cannot be reconciled with
fortnightly evidence the result is CANNOT_DETERMINE.

Each fortnight dict has keys: on_benefit (bool), reported (float), payslip (float | None).
"""
FREE_AREA = 100.0      # s1068-G12, p.65
LOWER_BAND = 150.0     # s1068-G15, p.65 (50% on the first $150 of excess)
LOWER_RATE = 0.5
UPPER_RATE = 0.6       # s1068-G16, p.66


def reduction(income):
    excess = max(0.0, income - FREE_AREA)
    return round(min(excess, LOWER_BAND) * LOWER_RATE + max(0.0, excess - LOWER_BAND) * UPPER_RATE, 2)


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
