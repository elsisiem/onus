# ONUS: backend ⇄ UI contract (server: `python3 server.py`, http://127.0.0.1:8787)

All responses are JSON. The UI is served at `/` from `ui/index.html`. Money values are numbers in dollars (2 dp).

## GET /api/rules
```json
{"act": {"title": "Social Security Act 1991, Volume 3", "compilation": "C2016C00230 (compilation 147, 10 Mar 2016)", "pages": 828,
         "muse": {"model": "muse-spark-1.3", "prompt_tokens": 353116, "seconds": 30.9}},
 "rules": [{"id": "1068-G7A", "page": 60, "quote": "...verbatim...", "verified": true, "role": "fortnight attribution"}]}
```

## POST /api/run
**Request:**
```json
{"earned": [26 numbers],        // true employment income per fortnight (the life the judge draws)
 "on_benefit": [26 booleans],   // receiving Newstart that fortnight?
 "payslips": false,             // are verified fortnightly payslips available to the PR?
 "pr": "averaging"}             // "averaging" | "free_area" | "cliff" | "legacy"
```
- `reported` income = `earned` in off-benefit fortnights. In on-benefit fortnights it is what was declared, and we assume honest declaration (the same as earned).
- The PR sees only the reported fortnights + `ato_annual_income` = sum(earned), and payslips if `payslips` is true.

**Response:**
```json
{"lawful": {"debt": 0.0, "status": "OK"},
 "pr": {"id": "averaging", "debt": 4875.0, "status": "OK", "misreads": "1068-G7A", "description": "..."},
 "letter": {"would_send": true, "amount": 4875.0, "lawful_amount": 0.0},
 "twin": {"earned": [26], "on_benefit": [26], "lawful": {"debt": 4875.0, "status": "OK"}, "pr": {"debt": 4875.0, "status": "OK"},
          "same_inputs_to_pr": true, "explanation": "..."},
 "sealed": {"hash": "sha256...", "sealed_at": "ISO time", "n_tests": 0, "failed": [{"id": "...", "family": "twin|boundary|attribution|life", "detail": "..."}]},
 "snap": {"latency_ms": 400, "input_tokens": 1360,
          "clauses": [{"id": "1068-G7A", "p": 0.89}],
          "disclosure_p": 0.06,
          "triage": {"choice": "statute-defect", "probabilities": {"statute-defect": 0.94}, "confidence": 0.92},
          "severity": 2.7, "route": "BLOCK"},          // BLOCK | PASS | ASK
 "verdict": {"route": "BLOCK", "headline": "BLOCKED: 1068-G7A fortnight attribution", "clause": "1068-G7A", "page": 60}}
```

## POST /api/ask
**Request:** `{"claim": "free text the judge types"}`

**Response:**
```json
{"verdict": "CONFIRMED", "rule_id": "1068-G12", "page": 65, "quote": "...", "latency_ms": 4200, "model": "muse-spark-1.3"}
```
`verdict` is one of `CONFIRMED` | `REFUTED` | `NOT IN EVIDENCE`.

## POST /api/redteam
**Request:** `{}`

**Response:**
```json
{"k": 3, "repo_ci_caught": 0, "onus_caught": 3,
 "mutants": [{"id": "averaging", "misreads": "1068-G7A", "description": "...", "repo_ci": "pass", "onus": "BLOCK"}]}
```

## POST /api/cert
**Request:** `{}`. **Response:** `{"statement": {in-toto Statement v1}, "sha256": "..."}`
