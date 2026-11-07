# ONUS: the burden of proof is on the code

**CI was green. The law wasn’t.** ONUS is a merge gate for AI-written changes to code that implements law. Its only source of truth is the statute.

Built solo at the AIE Code Summit 2026 Hackathon (Cerebral Valley, SF) for **Trust but Verify**: an independent verifier that writes its own tests without the implementer’s blind spots, stays reproducible, is hard to game, and blocks what’s below the standard.

## Why this exists
From 2015 to 2019, Australia’s **Robodebt** scheme averaged a person’s annual tax-office income evenly across 26 fortnights. It then raised about **470,000 debts** the law did not allow. In *Amato v Commonwealth* (2019) the Federal Court accepted that such a debt was not validly made. The government settled for about A$1.8 billion, and the 2023 Royal Commission called the scheme “crude and cruel”.

Code that implements law is about to be written by agents. **The tests an agent writes share the agent’s misunderstanding, so CI stays green.**

We asked Claude Code to implement the Robodebt-style ticket three different ways. It **refused all three times, citing the Federal Court** (transcripts in `law/claude_refusal_run*.txt`). That’s trust. ONUS is the verify, for the rules that never got a Royal Commission.

## What it does
1. **Reads the law.** Meta **Muse Spark** read the full text of *Social Security Act 1991, vol. 3* (828 pages, compilation C2016C00230) in **one call** (353,116 prompt tokens, 30.9 s). It returned each rule with its PDF page and a verbatim quote.
   - ONUS then **checks every quote against the Act’s text** (see `onus/law.py`): 6/6 verified. It auto-corrected s1223(1) from p.645 to **p.644**.
2. **Seals its tests before any PR exists.** The suite has three kinds of test, all derived from the statute:
   - boundary cases for 1068-G12, G15 and G16;
   - an attribution test for 1068-G7A;
   - a **twin test**: two people with identical inputs to the PR but different lawful debts. The suite is hashed (`law/sealed_suite.json`), so the coding agent can’t read or game it.
3. **Runs the PR on the person the judge draws.** It shows the letter the PR would have mailed, the lawful outcome and the twin.
4. **Decides with SubQ Snap**, a calibrated, sub-second decision model. One request per PR returns:
   - which clauses the diff rewrites (one yes/no per rule);
   - whether the PR description discloses the behaviour change;
   - a triage choice: statute defect / disclosed policy change / oracle doubt / statute ambiguity / no divergence;
   - a severity score.

   The route is **BLOCK**, **PASS** or **ASK A LAWYER**.
5. **Red team.** Deliberate misreadings of the Act: averaging (G7A), free-area conflation (G12), rate cliff (G15/G16). They were shaped by **Gemini Flash** from the rules alone (`law/mutants_gemini.json`).
   - **The repo’s own CI caught 0/3. ONUS caught 3/3.**
6. **Signs** an in-toto Statement (`predicateType: https://onus.dev/statute-conformance/v0.1`) with the rules, the seal, the decisions and the result.

## Measured on our keys today
| | Result |
|---|---|
| **Muse Spark**, full Act | 353K tokens in one call, 30.9 s; 6/6 quotes verified against the text |
| **Muse Spark**, “Ask the Act” | the claim “the free area is $150” came back **REFUTED**, citing 1068-G12 p.65 verbatim, in 5.7 s |
| **SubQ Snap**, averaging PR | G7A **0.93**, others ≤0.41; disclosure **0.009**; triage statute_defect **0.86** → BLOCK; **~0.4 s** |
| **SubQ Snap**, free-area PR | G12 **0.99** → BLOCK |
| **SubQ Snap**, rate-cliff PR | G15/G16 **0.99** → BLOCK |
| **SubQ Snap**, legacy code | every clause **0.00** → PASS |
| **The twin** (Sara: worked only while off benefit) | lawful **$0**. Her twin, with identical inputs to the PR: lawful **$10,725**. The averaging PR answers **$4,875 for both**, so it’s wrong for both |

## What is hard here
- Turning 828 pages of legislation into **verifiable** rules, with every quote checked against the source text and every page cite corrected.
- Tests that need **no expected values**. The twin property, “identical inputs, different lawful outcomes, so the only lawful answer is CANNOT_DETERMINE”, proves that *no* annual-only formula can be lawful.
- Independence by construction:
  - the tests are sealed before the PR;
  - the red team never sees the repo;
  - the decision model never writes code;
  - a deterministic oracle decides whether outputs differ, and Snap decides only what the difference *means* and who must act.

## Honesty
- **Real:** the statute is real (CC BY 4.0, legislation.gov.au).
- **Synthetic:** the people and the red-team PRs.
- **Scope:** the calculator is an illustrative single-adult Newstart income test with no partner, assets or remote-area rules.
- **Not legal advice.** ONUS routes genuine ambiguity to a lawyer.

## Run
```bash
cp .env.example .env   # META_API_KEY, SUBQ_API_KEY, GEMINI_API_KEY
python3 server.py      # http://127.0.0.1:8787
```

## Live vs cached during the demo
| Live | Cached (and why) |
|---|---|
| Each PR run on the drawn person; the twin; the sealed suite; SubQ decisions; Muse “Ask the Act”; the certificate | Muse’s full-Act extraction: a 31 s call, run earlier today and verified, stored in `law/rules_muse_raw.json` |
