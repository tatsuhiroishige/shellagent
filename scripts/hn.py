#!/usr/bin/env python3
"""hn — Hacker News terminal reader

Usage:
    hn              Show top 15 stories
    hn top [N]      Show top N stories (default 15)
    hn new [N]      Show newest N stories
    hn best [N]     Show best N stories
    hn read ID      Show story details + top comments
    hn open ID      Open story URL in $BROWSER or w3m
"""

import json
import os
import subprocess
import sys
import textwrap
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from urllib.request import urlopen

API = "https://hacker-news.firebaseio.com/v0"
COLS = int(os.environ.get("COLUMNS", 100))


def fetch_json(url: str):
    with urlopen(url) as r:
        return json.loads(r.read())


def fetch_item(item_id: int) -> dict:
    return fetch_json(f"{API}/item/{item_id}.json")


def fetch_stories(kind: str, count: int) -> list[dict]:
    ids = fetch_json(f"{API}/{kind}stories.json")[:count]
    items = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(fetch_item, i): i for i in ids}
        for f in as_completed(futures):
            item = f.result()
            if item:
                items.append(item)
    # Preserve original order
    order = {id_: i for i, id_ in enumerate(ids)}
    items.sort(key=lambda x: order.get(x["id"], 999))
    return items


def time_ago(ts: int) -> str:
    diff = int(datetime.now().timestamp()) - ts
    if diff < 60:
        return f"{diff}s"
    if diff < 3600:
        return f"{diff // 60}m"
    if diff < 86400:
        return f"{diff // 3600}h"
    return f"{diff // 86400}d"


def domain(url: str) -> str:
    if not url:
        return ""
    try:
        from urllib.parse import urlparse
        d = urlparse(url).netloc
        if d.startswith("www."):
            d = d[4:]
        return d
    except Exception:
        return ""


# ── Colors ──

BOLD = "\033[1m"
DIM = "\033[2m"
ORANGE = "\033[38;5;208m"
CYAN = "\033[36m"
GREEN = "\033[32m"
RESET = "\033[0m"


def print_stories(items: list[dict]):
    for i, item in enumerate(items, 1):
        title = item.get("title", "(no title)")
        url = item.get("url", "")
        score = item.get("score", 0)
        by = item.get("by", "?")
        age = time_ago(item.get("time", 0))
        comments = item.get("descendants", 0)
        dom = domain(url)
        id_ = item["id"]

        num = f"{ORANGE}{i:>3}.{RESET}"
        score_s = f"{BOLD}{score:>4}↑{RESET}"
        title_s = f"{BOLD}{title}{RESET}"
        dom_s = f" {DIM}({dom}){RESET}" if dom else ""
        meta = f"     {DIM}{by} | {age} | {comments} comments | id:{id_}{RESET}"

        print(f"{num} {score_s} {title_s}{dom_s}")
        print(meta)


def fetch_comments(item: dict, depth: int = 0, max_depth: int = 2, max_per_level: int = 5) -> list[tuple[int, dict]]:
    """Fetch comment tree, returns [(depth, item), ...]"""
    results = []
    kids = item.get("kids", [])[:max_per_level]
    if not kids or depth > max_depth:
        return results

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fetch_item, kid): kid for kid in kids}
        comments = {}
        for f in as_completed(futures):
            c = f.result()
            if c and c.get("type") == "comment" and not c.get("deleted") and not c.get("dead"):
                comments[c["id"]] = c

    for kid in kids:
        if kid in comments:
            c = comments[kid]
            results.append((depth, c))
            results.extend(fetch_comments(c, depth + 1, max_depth, max_per_level))

    return results


def strip_html(text: str) -> str:
    """Simple HTML tag stripping + entity decode."""
    import re
    text = re.sub(r'<p>', '\n\n', text)
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&#x27;', "'").replace('&quot;', '"').replace('&#x2F;', '/')
    return text.strip()


def cmd_read(item_id: int):
    item = fetch_item(item_id)
    if not item:
        print("Story not found")
        return

    title = item.get("title", "(no title)")
    url = item.get("url", "")
    score = item.get("score", 0)
    by = item.get("by", "?")
    age = time_ago(item.get("time", 0))
    comments_count = item.get("descendants", 0)
    text = item.get("text", "")

    print(f"\n{BOLD}{title}{RESET}")
    if url:
        print(f"{CYAN}{url}{RESET}")
    print(f"{DIM}{score}↑ by {by} | {age} | {comments_count} comments{RESET}")

    if text:
        print(f"\n{strip_html(text)}")

    print(f"\n{'─' * min(COLS, 80)}")
    print(f"{BOLD}Top Comments:{RESET}\n")

    comment_tree = fetch_comments(item)
    if not comment_tree:
        print(f"  {DIM}(no comments){RESET}")
        return

    wrap_width = min(COLS, 80)
    for depth, c in comment_tree:
        indent = "  " * (depth + 1)
        by_c = c.get("by", "?")
        age_c = time_ago(c.get("time", 0))
        body = strip_html(c.get("text", ""))

        header = f"{indent}{GREEN}{by_c}{RESET} {DIM}{age_c}{RESET}"
        print(header)

        for para in body.split("\n"):
            if para.strip():
                available = wrap_width - len(indent) - 2
                wrapped = textwrap.fill(para.strip(), width=max(available, 40))
                for line in wrapped.split("\n"):
                    print(f"{indent}  {line}")
        print()


def cmd_open(item_id: int):
    item = fetch_item(item_id)
    if not item:
        print("Story not found")
        return
    url = item.get("url", f"https://news.ycombinator.com/item?id={item_id}")
    browser = os.environ.get("BROWSER", "w3m")
    print(f"Opening: {url}")
    subprocess.run([browser, url])


def main():
    args = sys.argv[1:]

    if not args or args[0] == "top":
        count = int(args[1]) if len(args) > 1 else 15
        print(f"\n{BOLD}{ORANGE}━━━ Hacker News Top {count} ━━━{RESET}\n")
        items = fetch_stories("top", count)
        print_stories(items)

    elif args[0] == "new":
        count = int(args[1]) if len(args) > 1 else 15
        print(f"\n{BOLD}{ORANGE}━━━ Hacker News New {count} ━━━{RESET}\n")
        items = fetch_stories("new", count)
        print_stories(items)

    elif args[0] == "best":
        count = int(args[1]) if len(args) > 1 else 15
        print(f"\n{BOLD}{ORANGE}━━━ Hacker News Best {count} ━━━{RESET}\n")
        items = fetch_stories("best", count)
        print_stories(items)

    elif args[0] == "read":
        if len(args) < 2:
            print("Usage: hn read <ID>")
            sys.exit(1)
        cmd_read(int(args[1]))

    elif args[0] == "open":
        if len(args) < 2:
            print("Usage: hn open <ID>")
            sys.exit(1)
        cmd_open(int(args[1]))

    else:
        print(__doc__)


if __name__ == "__main__":
    main()
