# HF Daily Papers Newsfeed

Automated pipeline that pulls papers from Hugging Face Daily Papers, normalizes entries, applies topic scoring, generates a Markdown digest, and publishes an RSS feed.

## What is implemented

- Collector for latest Daily Papers date (or explicit `--date`)
- Parser for paper IDs from Hugging Face date pages
- Per-paper metadata extraction (title, abstract snippet, external arXiv link when available)
- Topic scoring using configurable weighted profile (`config/scoring_profile.json`)
- Deterministic summary + “why it matters” generation
- Outputs:
  - `data/raw/YYYY-MM-DD.html`
  - `data/normalized/YYYY-MM-DD.jsonl`
  - `digest/YYYY-MM-DD.md`
  - `feed.xml`
  - `data/state/latest.json`
- Unit tests for core parsing/scoring logic
- GitHub Actions daily workflow

---

## Quick start

```bash
git clone https://github.com/inigos-agent/hf-daily-papers-newsfeed-plan.git
cd hf-daily-papers-newsfeed-plan

# run tests
PYTHONPATH=src python3 -m unittest discover -s tests -p "test_*.py"

# run pipeline on latest date
PYTHONPATH=src python3 run.py

# run pipeline for explicit date
PYTHONPATH=src python3 run.py --date 2026-02-20

# test mode (faster)
PYTHONPATH=src python3 run.py --limit 5
```

---

## Repository structure

```text
hf-daily-papers-newsfeed-plan/
  config/
    scoring_profile.json
    SCORING.md
  data/
    raw/
    normalized/
    state/
  digest/
  src/hf_daily_papers_newsfeed/
    pipeline.py
  tests/
    test_pipeline.py
  run.py
  feed.xml                # generated
  .github/workflows/daily.yml
```

---

## Data schema (`data/normalized/YYYY-MM-DD.jsonl`)

Each line is one JSON record:

```json
{
  "paper_id": "2602.10693",
  "title": "...",
  "source_url": "https://huggingface.co/papers/2602.10693",
  "external_url": "https://arxiv.org/abs/2602.10693",
  "authors": ["..."],
  "abstract": "...",
  "date_seen": "2026-02-20",
  "topics": ["llm", "efficiency"],
  "score": 0.45,
  "summary": "...",
  "why_it_matters": "..."
}
```

---

## Scheduling

GitHub Actions runs daily at `08:10 UTC` and commits generated digest/feed files back to `main`.

If no changes are detected, no commit is made.

---

## Notes / limitations

- This is a source-page parser (no official HF Daily Papers API used).
- Metadata extraction is best-effort from page/meta tags.
- For production-grade summarization, replace deterministic summary with an LLM step and add human QA gates.

---

## Next upgrade ideas

- Better author extraction from structured JSON blobs
- Enrichment from arXiv API (categories, publication date)
- Telegram/Discord publisher
- Topic relevance model (embedding/classifier) instead of keyword rules
- Add de-duplication across multiple days into a persistent index
