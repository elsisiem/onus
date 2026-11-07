# ONUS: 2:45 stage script

Tone: calm and exact. Robodebt hurt real people, and it's the reason this tool exists, not a gag.

| t | Screen | Say | Judge |
|---|---|---|---|
| 0:00 | Hero: "CI was green. The law wasn't." | "Australia's Robodebt averaged people's yearly income across fortnights and sent **470,000 debts the law didn't allow**. Code like that is about to be written by AI agents. When we asked Claude Code to build it, it refused three times and cited the Federal Court. That's trust. ONUS is the verify." | — |
| 0:20 | The Act pane | "ONUS reads the law first. Meta's **Muse Spark read all 828 pages** of the Social Security Act in one call. Every rule comes back with its page and a verbatim quote, and we check each quote against the text. It even caught its own page cite being one off." | — |
| 0:40 | Income canvas, Sara preset | "Before any AI writes a line, ONUS **seals** tests from the statute. Now: **draw anyone's year.**" | **drags bars / toggles benefit** |
| 0:55 | Verdict band + letter | "This PR, 'use the ATO annual income feed, no behaviour change', would mail Sara **$4,875**. The law says she owes **$0**." | — |
| 1:10 | Twin panel | "Here's her twin. Same annual income, same reports. **Identical inputs to the PR.** But the twin earned while on benefit, so the twin lawfully owes $10,725. The PR says $4,875 to both. **No formula that only sees the yearly figure can be right for both.** The only lawful answer is 'cannot determine'. That test needs no expected values." | — |
| 1:35 | SubQ block | "**SubQ Snap** decides in about 400 milliseconds. Which clause did the diff rewrite? **G7A, fortnight attribution, 0.93.** Did the description disclose the change? **0.01.** Statute defect at 0.86: **blocked.** A diff tells you the outputs differ; Snap tells you what that means and who has to act." | — |
| 2:00 | Red team | "**Gemini** wrote deliberate misreadings of the Act from the rules alone. It never saw our code. **The repo's own CI caught 0 of 3. ONUS caught 3 of 3**, and Snap named the exact clause each one broke." | **clicks Red-team** |
| 2:20 | Ask the Act | "Ask it anything about the Act." | **types a claim** → Muse returns CONFIRMED / REFUTED / NOT IN EVIDENCE with page + quote (about 6 s) |
| 2:35 | Certificate + press | "Every decision is signed: the rules, the seal, the result. The burden of proof is on the code." | — |

**If Muse is slow:** show the cached answer and say so. Never debug on stage.

## Q&A (15 seconds each)
- **"What if Muse misreads the Act?"**
  - Every quote is checked verbatim against the source. Unverified rules are flagged, and it auto-corrected a page cite today.
  - The tests are sealed from those rules, so a misreading is *visible and versioned*, not silent.
  - Where the statute is ambiguous, Snap routes to **ASK A LAWYER** instead of guessing.
- **"Snap accuracy?"**
  - On today's three red-team PRs plus legacy, the clause map named the exact misread clause each time: G12 0.99, G15/G16 0.99, G7A 0.93, legacy all 0.00.
  - Small n, and we say so. The deterministic oracle decides *whether* outputs differ; Snap decides *what it means*.
- **"The people are synthetic."**
  - Yes, and labelled. The statute is real. The twin property is real mathematics: identical inputs plus different lawful outcomes means the only lawful answer is CANNOT_DETERMINE.
  - Next: Royal Commission case studies as personas.
- **"Who buys this?"**
  - Anyone whose code implements rules: payroll, tax and lending engines, insurers, benefits modernization.
  - Agents are about to write that code. ONUS is the gate on every PR, priced per repo.
- **"Why not just better tests?"**
  - The tests are written by the same author with the same misunderstanding. ONUS's tests come from the statute and are sealed before the PR exists.
- **"Why didn't Claude write the bug?"**
  - It refused (transcripts in the repo). The red-team PRs are deliberately planted misreadings. Not every model, and not every rule, has a famous court case to warn it.
