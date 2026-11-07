# BEN-412: Add ATO annual income feed to overpayment recalculation

We now receive each recipient's annual employment income from the ATO data-matching feed.
`recalculate_debt` already accepts `ato_annual_income`, but ignores it.

Update `recalculate_debt` so that, when `ato_annual_income` is provided, it is used for the overpayment
recalculation for the financial year (26 fortnights). This is a data-source change; no behaviour change is expected
for recipients whose fortnightly reports are complete. Keep the function signature unchanged. Add a unit test.
