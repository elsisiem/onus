"""The statute as ONUS sees it: rules extracted by Muse Spark from the full 828-page volume,
each quote verified against the page-marked text of the Act."""
import json, re, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACT = {"title": "Social Security Act 1991, Volume 3", "compilation": "C2016C00230 (compilation 147, in force 10 Mar 2016)",
       "pages": 828, "licence": "CC BY 4.0, legislation.gov.au",
       "muse": {"model": "muse-spark-1.3", "prompt_tokens": 353116, "seconds": 30.9, "reasoning_tokens": 3444}}
ROLES = {"1068-G7A": "fortnight attribution", "1068-G12": "ordinary income free area", "1068-G15": "lower range reduction (50%)",
         "1068-G16": "upper range reduction (60%)", "1073B": "daily attribution of employment income", "1223-1": "debt due to the Commonwealth"}
_norm = lambda s: re.sub(r"[^a-z0-9$%]+", " ", s.lower()).strip()


def _pages():
    path = os.path.join(ROOT, "runs", "vol3_paged.txt")
    if not os.path.exists(path):
        return {}
    text = open(path, encoding="utf-8", errors="ignore").read()
    parts = re.split(r"=== PDF PAGE (\d+) ===", text)
    return {int(parts[i]): parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def load_rules():
    raw = json.load(open(os.path.join(ROOT, "law", "rules_muse_raw.json")))["rules"]
    pages = _pages()
    out = []
    for r in raw:
        q, page, found = _norm(r["quote"]), r["pdf_page"], None
        for p in [page, page - 1, page + 1, page - 2, page + 2]:
            if p in pages and q[:120] in _norm(pages[p]):
                found = p
                break
        out.append({"id": r["id"], "page": found or page, "muse_page": page, "quote": r["quote"],
                    "verified": found is not None, "page_corrected": found is not None and found != page,
                    "role": ROLES.get(r["id"], "")})
    return out


def page_text(page_numbers):
    pages = _pages()
    return {p: pages.get(p, "")[:6000] for p in page_numbers}
