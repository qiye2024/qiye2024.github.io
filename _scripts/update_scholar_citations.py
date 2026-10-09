#!/usr/bin/env python3
"""Refresh the persistent Google Scholar citation cache (standard library only).

Google Scholar may block automated requests. On any error or unrecognized page,
retain the last known value; NEVER replace it with 0 or N/A.
"""

from html.parser import HTMLParser
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "_data" / "scholar_citations.yml"
BIBLIOGRAPHY = ROOT / "_bibliography" / "papers.bib"
SOCIALS = ROOT / "_data" / "socials.yml"


class ScholarPage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.descriptions = []

    def handle_starttag(self, tag, attrs):
        if tag != "meta":
            return
        attrs = dict(attrs)
        if attrs.get("name", "").lower() == "description" or attrs.get("property", "").lower() == "og:description":
            self.descriptions.append(attrs.get("content", ""))


def parse_citation_count(html):
    page = ScholarPage()
    page.feed(html)
    for description in page.descriptions:
        match = re.search(r"\bCited by\s+([\d,]+)\b", description, re.IGNORECASE)
        if match:
            return int(match.group(1).replace(",", ""))
    return None


def read_cache(path):
    """Read the deliberately simple key: integer YAML mapping without PyYAML."""
    result = {}
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#") or line == "{}":
            continue
        match = re.fullmatch(r"([a-zA-Z0-9_-]+):\s*(\d+)", line)
        if not match:
            raise ValueError(f"Unexpected citation cache format at line {lineno}: {line}")
        result[match.group(1)] = int(match.group(2))
    return result


def write_cache(path, counts):
    header = (
        "# Last successfully retrieved Google Scholar citation counts.\n"
        "# Updated automatically; if scraping fails, existing counts are retained.\n"
        "# Google Scholar can block automated requests, so values may be stale.\n"
    )
    contents = header + "".join(f"{key}: {counts[key]}\n" for key in sorted(counts))
    path.write_text(contents, encoding="utf-8")


def article_ids(bib_text):
    return list(dict.fromkeys(re.findall(r"\bgoogle_scholar_id\s*=\s*\{([a-zA-Z0-9_-]+)\}", bib_text)))


def scholar_user_id(socials_text):
    match = re.search(r"^scholar_userid:\s*([a-zA-Z0-9_-]+)\s*(?:#.*)?$", socials_text, re.MULTILINE)
    if not match:
        raise ValueError("Cannot find scholar_userid in _data/socials.yml")
    return match.group(1)


def fetch_citation_count(user_id, article_id):
    params = urlencode({"view_op": "view_citation", "hl": "en", "user": user_id,
                        "citation_for_view": f"{user_id}:{article_id}"})
    url = f"https://scholar.google.com/citations?{params}"
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; AcademicWebsiteCitationCache/1.0)"})
    with urlopen(request, timeout=18) as response:
        html = response.read().decode("utf-8", errors="replace")
    return parse_citation_count(html)


def update_counts(counts, fetch, ids, user_id):
    updated = dict(counts)
    for index, article_id in enumerate(ids):
        if index:
            time.sleep(2)
        try:
            count = fetch(user_id, article_id)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            print(f"{article_id}: unable to fetch ({exc}); preserving previous value")
            continue
        if count is None:
            print(f"{article_id}: citation count not found; preserving previous value")
            continue
        old = updated.get(article_id)
        if old is not None and count < old:
            print(f"{article_id}: fetched {count} < cached {old}; preserving prior value for review")
            continue
        updated[article_id] = count
        print(f"{article_id}: {count} citations" + (" (updated)" if old != count else " (unchanged)"))
    return updated


def main():
    counts = read_cache(CACHE)
    ids = article_ids(BIBLIOGRAPHY.read_text(encoding="utf-8"))
    user_id = scholar_user_id(SOCIALS.read_text(encoding="utf-8"))
    if not ids:
        raise ValueError("No google_scholar_id entries found in papers.bib")
    updated = update_counts(counts, fetch_citation_count, ids, user_id)
    if updated != counts:
        write_cache(CACHE, updated)
        print("Saved updated citation counts.")
    else:
        print("No valid new counts; existing cache left untouched.")


if __name__ == "__main__":
    main()
