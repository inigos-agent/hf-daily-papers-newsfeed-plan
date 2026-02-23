from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import sys
import urllib.request
import xml.sax.saxutils as saxutils
from dataclasses import dataclass, asdict
from typing import Iterable, Any

HF_BASE = "https://huggingface.co"
UA = "hf-daily-papers-newsfeed/0.1 (+https://github.com/inigos-agent/hf-daily-papers-newsfeed-plan)"


@dataclass
class Paper:
    paper_id: str
    title: str
    source_url: str
    external_url: str
    authors: list[str]
    abstract: str
    date_seen: str
    topics: list[str]
    score: float
    summary: str
    why_it_matters: str


def http_get(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def find_latest_date_from_homepage(home_html: str) -> str | None:
    m = re.search(r"/papers/date/(\d{4}-\d{2}-\d{2})", home_html)
    return m.group(1) if m else None


def extract_paper_ids(date_page_html: str) -> list[str]:
    ids = re.findall(r"/papers/(\d{4}\.\d{5})(?:[#\"/?]|$)", date_page_html)
    seen = set()
    out = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def extract_daily_papers_records(date_page_html: str) -> list[dict[str, Any]]:
    unescaped = html.unescape(date_page_html)
    key = '"dailyPapers":'
    i = unescaped.find(key)
    if i == -1:
        return []
    s = unescaped[i + len(key):]
    start = s.find('[')
    if start == -1:
        return []

    depth = 0
    end = None
    for j, ch in enumerate(s[start:]):
        if ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
            if depth == 0:
                end = start + j + 1
                break

    if end is None:
        return []

    try:
        return json.loads(s[start:end])
    except json.JSONDecodeError:
        return []


def load_scoring_profile(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def score_topics(title: str, abstract: str, profile: dict[str, Any]) -> tuple[list[str], float]:
    text = (title + "\n" + abstract).lower()
    categories = profile.get("categories", {})
    base_per_hit = float(profile.get("base_per_hit", 0.15))
    cap_per_category = float(profile.get("cap_per_category", 1.0))

    matched: list[str] = []
    score = 0.0

    for topic, cfg in categories.items():
        kws = cfg.get("keywords", []) if isinstance(cfg, dict) else []
        weight = float(cfg.get("weight", 1.0)) if isinstance(cfg, dict) else 1.0

        hit = 0
        for kw in kws:
            if str(kw).lower() in text:
                hit += 1
        if hit:
            matched.append(topic)
            score += min(cap_per_category, base_per_hit * hit) * weight

    if not matched:
        matched = ["other"]
    return matched, min(1.0, score)


def summarize(title: str, abstract: str, topics: list[str]) -> tuple[str, str]:
    clean = re.sub(r"\s+", " ", abstract).strip()
    if len(clean) > 240:
        clean = clean[:237].rstrip() + "..."
    if not clean:
        clean = "No abstract snippet available from source page."
    why = f"Relevant for {', '.join(topics[:3])} workflows and daily paper tracking."
    return clean, why


def digest_markdown(date_str: str, papers: list[Paper]) -> str:
    lines = [f"# Daily Papers Digest — {date_str}", "", f"Papers collected: **{len(papers)}**", ""]
    for i, p in enumerate(sorted(papers, key=lambda x: x.score, reverse=True), 1):
        lines += [
            f"## {i}) {p.title or p.paper_id}",
            f"- **Topics:** {', '.join(p.topics)}",
            f"- **Score:** {p.score:.2f}",
            f"- **Summary:** {p.summary}",
            f"- **Why it matters:** {p.why_it_matters}",
            f"- **Links:** [HF]({p.source_url}) · [External]({p.external_url})",
            "",
        ]
    return "\n".join(lines).strip() + "\n"


def rss_xml(site_url: str, items: list[Paper], title: str = "HF Daily Papers Feed") -> str:
    now = dt.datetime.now(dt.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0"><channel>',
        f"<title>{saxutils.escape(title)}</title>",
        f"<link>{saxutils.escape(site_url)}</link>",
        "<description>Daily Hugging Face papers digest</description>",
        f"<lastBuildDate>{now}</lastBuildDate>",
    ]
    for p in sorted(items, key=lambda x: x.score, reverse=True)[:50]:
        guid = hashlib.sha1((p.paper_id + p.date_seen).encode()).hexdigest()
        out += [
            "<item>",
            f"<title>{saxutils.escape(p.title or p.paper_id)}</title>",
            f"<link>{saxutils.escape(p.source_url)}</link>",
            f"<guid isPermaLink=\"false\">{guid}</guid>",
            f"<description>{saxutils.escape(p.summary)}</description>",
            "</item>",
        ]
    out.append("</channel></rss>")
    return "\n".join(out)


def ensure_dirs(root: str) -> None:
    for d in ["data/raw", "data/normalized", "data/state", "digest"]:
        os.makedirs(os.path.join(root, d), exist_ok=True)


def run(root: str, target_date: str | None = None, limit: int | None = None) -> list[Paper]:
    ensure_dirs(root)
    scoring_profile = load_scoring_profile(os.path.join(root, "config", "scoring_profile.json"))

    if not target_date:
        home = http_get(f"{HF_BASE}/papers")
        target_date = find_latest_date_from_homepage(home)
        if not target_date:
            raise RuntimeError("Could not determine latest date from HF /papers page")

    date_html = http_get(f"{HF_BASE}/papers/date/{target_date}")
    ids = extract_paper_ids(date_html)
    records = extract_daily_papers_records(date_html)

    rec_by_id: dict[str, dict[str, Any]] = {}
    for r in records:
        p = r.get("paper", {}) if isinstance(r, dict) else {}
        pid = p.get("id")
        if pid:
            rec_by_id[pid] = r

    if limit:
        ids = ids[:limit]

    raw_path = os.path.join(root, "data", "raw", f"{target_date}.html")
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(date_html)

    papers: list[Paper] = []
    for pid in ids:
        try:
            r = rec_by_id.get(pid, {})
            p = r.get("paper", {}) if isinstance(r, dict) else {}
            title = (r.get("title") or p.get("title") or "").strip()
            abstract = (r.get("summary") or p.get("summary") or "").strip()
            authors = []
            for a in (p.get("authors") or []):
                if isinstance(a, dict) and a.get("name"):
                    authors.append(str(a.get("name")))
            external = f"https://arxiv.org/abs/{pid}"
            url = f"{HF_BASE}/papers/{pid}"

            topics, score = score_topics(title, abstract, scoring_profile)
            summary, why = summarize(title, abstract, topics)
            papers.append(
                Paper(
                    paper_id=pid,
                    title=title,
                    source_url=url,
                    external_url=external,
                    authors=authors,
                    abstract=abstract,
                    date_seen=target_date,
                    topics=topics,
                    score=score,
                    summary=summary,
                    why_it_matters=why,
                )
            )
        except Exception as e:
            print(f"WARN: failed {pid}: {e}", file=sys.stderr)

    norm_path = os.path.join(root, "data", "normalized", f"{target_date}.jsonl")
    with open(norm_path, "w", encoding="utf-8") as f:
        for p in papers:
            f.write(json.dumps(asdict(p), ensure_ascii=False) + "\n")

    digest = digest_markdown(target_date, papers)
    with open(os.path.join(root, "digest", f"{target_date}.md"), "w", encoding="utf-8") as f:
        f.write(digest)

    with open(os.path.join(root, "feed.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml("https://huggingface.co/papers", papers))

    state = {
        "last_run_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "target_date": target_date,
        "count": len(papers),
        "paper_ids": [p.paper_id for p in papers],
    }
    with open(os.path.join(root, "data", "state", "latest.json"), "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    return papers


def cli(argv: Iterable[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Build HF daily papers digest/feed")
    p.add_argument("--date", help="Target date YYYY-MM-DD (default: latest date on HF)")
    p.add_argument("--limit", type=int, help="Limit number of papers for testing")
    args = p.parse_args(list(argv) if argv is not None else None)

    cwd = os.getcwd()
    root = cwd if os.path.exists(os.path.join(cwd, "config", "scoring_profile.json")) else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    papers = run(root=root, target_date=args.date, limit=args.limit)
    print(f"OK: generated {len(papers)} papers")
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
