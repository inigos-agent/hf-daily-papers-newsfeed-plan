# Hugging Face Daily Papers → News Feed (Implementation Plan)

## Objective
Create an automated news feed pipeline that ingests papers from Hugging Face’s Daily Papers page, filters/summarizes them, and publishes clean daily updates (e.g., Telegram, RSS, Markdown digest, or email-ready output).

---

## 1) Product Definition

### Inputs
- Primary source: Hugging Face Daily Papers page (daily updates)
- Optional enrichments: arXiv metadata, GitHub repos, citation metrics, author/institution tags

### Outputs
- Daily digest (Markdown)
- Optional RSS/Atom feed
- Optional Telegram push message(s)
- Archive of historical digests in repo

### User value
- High-signal daily research scan
- Consistent format and relevance filters
- Searchable history by date/topic

---

## 2) Pipeline Architecture

1. **Collector**
   - Fetch Daily Papers page at fixed schedule (e.g., 08:00 UTC daily)
   - Parse paper list and metadata fields

2. **Normalizer**
   - Convert entries to canonical schema:
     - `paper_id`, `title`, `authors`, `url`, `abstract`, `date`, `tags`

3. **Deduplicator**
   - Deduplicate by stable key (arXiv ID, DOI, or normalized URL/title hash)

4. **Scorer/Filter**
   - Rule-based or model-based relevance scoring
   - Example filters: LLMs, agents, interpretability, multimodal, RL

5. **Summarizer**
   - Generate concise summaries (1–3 lines per paper)
   - Include “why it matters” bullet

6. **Publisher**
   - Generate `digest/YYYY-MM-DD.md`
   - Update `feed.xml` (if RSS enabled)
   - Optional send via Telegram

7. **Storage**
   - Keep raw snapshots + normalized JSON + published digest files

---

## 3) Proposed Repo Structure

```text
hf-daily-papers-newsfeed/
  README.md
  docs/
    architecture.md
    operations.md
  data/
    raw/
    normalized/
    state/
  digest/
    2026-02-23.md
  src/
    collect.py
    normalize.py
    score.py
    summarize.py
    publish.py
  config/
    topics.yaml
    sources.yaml
  .github/workflows/
    daily.yml
```

---

## 4) Data Schema (v0)

```json
{
  "paper_id": "arxiv:2501.12345",
  "title": "Paper Title",
  "authors": ["A", "B"],
  "source_url": "https://huggingface.co/papers/...",
  "external_url": "https://arxiv.org/abs/...",
  "date_seen": "2026-02-23",
  "topics": ["llm", "agents"],
  "score": 0.82,
  "summary": "Two-line summary",
  "why_it_matters": "Potential impact on ..."
}
```

---

## 5) Scheduling & Operations

### Schedule
- Daily run at fixed UTC time (GitHub Actions cron or OpenClaw cron)
- Optional midday incremental refresh

### State
- Persist `last_run`, last seen IDs, and dedupe index in `data/state/`

### Failure handling
- If source parse fails:
  - keep last successful feed
  - raise alert (issue/telegram)
  - retry with backoff

---

## 6) Quality Controls

- Parse validation (required fields present)
- Duplicate detection checks
- Summary length + style constraints
- Link health checks (optional)
- Manual override list for must-include/must-exclude papers

---

## 7) Security & Compliance

- No scraping that violates ToS; prefer official/public endpoints where available
- Respect rate limits and robots policies
- Keep secrets (bot tokens/API keys) in GitHub Secrets, never in repo

---

## 8) Milestone Plan

### Milestone 1 (MVP, 1–2 days)
- Collect + parse + dedupe + daily markdown digest

### Milestone 2 (2–4 days)
- Topic scoring + improved summaries + historical archive

### Milestone 3 (optional)
- RSS generation + Telegram push + analytics dashboard

---

## 9) Example Digest Format

```markdown
# Daily Papers Digest — 2026-02-23

## Top Picks

### 1) Paper title
- **Why it matters:** ...
- **Summary:** ...
- **Links:** [HF](...), [arXiv](...), [Code](...)

### 2) Paper title
...

## Honorable Mentions
- ...
```

---

## 10) Recommended First Build Path

Start simple and deterministic:
1. Build parser and save normalized JSON
2. Produce plain markdown digest without LLM summarization
3. Add summarization and topic ranking after parser stability
4. Add delivery channels last

This minimizes fragility and makes debugging easier.

---

## Next Step (pending approval)
Upon approval, implementation will begin with MVP parser + digest generation and a scheduled daily workflow.
