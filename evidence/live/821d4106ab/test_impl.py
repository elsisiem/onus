import unittest
from impl import recalculate_debt


class TestRecalculateDebt(unittest.TestCase):
    def test_income_below_threshold(self):
        fortnights = [
            {"on_benefit": True, "reported": 50.0, "payslip": 80.0}
        ]
        result = recalculate_debt(fortnights)
        self.assertEqual(result, {"debt": 0.0, "status": "OK"})

    def test_single_taper_reduction(self):
        fortnights = [
            {"on_benefit": True, "reported": 100.0, "payslip": 200.0}
        ]
        result = recalculate_debt(fortnights)
        self.assertEqual(result, {"debt": 50.0, "status": "OK"})

    def test_high_income_single_taper(self):
        fortnights = [
            {"on_benefit": True, "reported": 100.0, "payslip": 400.0}
        ]
        result = recalculate_debt(fortnights)
        self.assertEqual(result, {"debt": 150.0, "status": "OK"})

    def test_not_on_benefit_ignored(self):
        fortnights = [
            {"on_benefit": False, "reported": 100.0, "payslip": 400.0}
        ]
        result = recalculate_debt(fortnights)
        self.assertEqual(result, {"debt": 0.0, "status": "OK"})

    def test_payslip_none_uses_reported(self):
        fortnights = [
            {"on_benefit": True, "reported": 200.0, "payslip": None}
        ]
        result = recalculate_debt(fortnights)
        self.assertEqual(result, {"debt": 0.0, "status": "OK"})

    def test_actual_less_than_reported_no_debt(self):
        fortnights = [
            {"on_benefit": True, "reported": 300.0, "payslip": 200.0}
        ]
        result = recalculate_debt(fortnights)
        self.assertEqual(result, {"debt": 0.0, "status": "OK"})

    def test_ato_reconciliation_ok_when_evidenced_matches(self):
        fortnights = [
            {"on_benefit": True, "reported": 100.0, "payslip": 200.0}
        ]
        result = recalculate_debt(fortnights, ato_annual_income=200.0)
        self.assertEqual(result, {"debt": 50.0, "status": "OK"})

    def test_ato_reconciliation_cannot_determine_missing_payslip(self):
        fortnights = [
            {"on_benefit": True, "reported": 100.0, "payslip": None}
        ]
        result = recalculate_debt(fortnights, ato_annual_income=500.0)
        self.assertEqual(result, {"debt": 0.0, "status": "CANNOT_DETERMINE"})

    def test_ato_reconciliation_all_payslips_present(self):
        fortnights = [
            {"on_benefit": True, "reported": 100.0, "payslip": 200.0}
        ]
        result = recalculate_debt(fortnights, ato_annual_income=500.0)
        self.assertEqual(result, {"debt": 50.0, "status": "OK"})


if __name__ == "__main__":
    unittest.main()
