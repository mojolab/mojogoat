#!/usr/bin/env python3
"""
goatwatch — live view of MojoGOAT relationship growth, grouped by goat.

Usage:
    python goatwatch.py                   # default: localhost:5000, 2s refresh
    MOJOGOAT_URL=http://host:5000 python goatwatch.py
    GOATWATCH_INTERVAL=5 python goatwatch.py
    python goatwatch.py --interval 3 --url http://localhost:5000
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime


def _fetch(base_url: str, path: str, timeout: float = 3.0):
    try:
        with urllib.request.urlopen(f"{base_url}{path}", timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return None


def _fmt_taxonomy(taxonomy: dict) -> str:
    if not taxonomy:
        return "—"
    parts = [f"{k}:{v}" for k, v in sorted(taxonomy.items(), key=lambda x: -x[1])]
    line = "  ".join(parts)
    return line[:52] + "…" if len(line) > 53 else line


def _render(base_url: str, prev_counts: dict, width: int = 76) -> tuple[dict, str]:
    status = _fetch(base_url, "/api/status")
    if not status:
        return prev_counts, f"\n  ✗  Cannot reach {base_url}\n"

    active_name = (status.get("active_goat") or {}).get("name")
    goats = status.get("goats", [])
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rows = []
    new_counts: dict = {}

    for g in goats:
        name = g["name"]
        gtype = g["type"]
        marker = "●" if name == active_name else " "

        summary = _fetch(base_url, f"/api/goats/{name}/summary")

        if summary and "error" not in summary and summary.get("rel_count") is not None:
            nc = summary["node_count"]
            rc = summary["rel_count"]
            taxonomy = summary.get("taxonomy", {})
            prev = prev_counts.get(name)
            delta = f"+{rc - prev}" if prev is not None and rc > prev else ""
            new_counts[name] = rc
            story_str = _fmt_taxonomy(taxonomy)
        elif summary and summary.get("note"):
            nc = rc = "—"
            delta = ""
            story_str = f"({summary['note'][:40]})"
            if name in prev_counts:
                new_counts[name] = prev_counts[name]
        else:
            nc = rc = "—"
            delta = ""
            story_str = (summary or {}).get("error", "unreachable")
            if name in prev_counts:
                new_counts[name] = prev_counts[name]

        short = name[:26] if len(name) > 26 else name
        rows.append((marker, short, gtype, nc, rc, delta, story_str))

    # ── build output ──────────────────────────────────────────────
    bar = "━" * width
    sep = "  " + "─" * (width - 2)
    header = (
        f"  {'GOAT':<28} {'TYPE':<10} {'NODES':>5}  {'RELS':>5}  {'Δ':>4}  STORIES"
    )

    lines = [
        bar,
        f"  MojoGOAT Watch   {now}   ↺ {interval:.0f}s",
        bar,
        "",
        header,
        sep,
    ]

    for marker, short, gtype, nc, rc, delta, story_str in rows:
        nc_s = str(nc) if nc != "—" else "—"
        rc_s = str(rc) if rc != "—" else "—"
        lines.append(
            f"  {marker} {short:<27} {gtype:<10} {nc_s:>5}  {rc_s:>5}  {delta:>4}  {story_str}"
        )

    lines += [
        "",
        bar,
        f"  {base_url}   Ctrl-C to quit",
        "",
    ]

    return new_counts, "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live MojoGOAT relationship watcher")
    parser.add_argument("--url", default=os.environ.get("MOJOGOAT_URL", "http://localhost:5000"))
    parser.add_argument("--interval", "-i", type=float,
                        default=float(os.environ.get("GOATWATCH_INTERVAL", "2")))
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    interval = args.interval

    prev_counts: dict = {}
    try:
        while True:
            prev_counts, output = _render(base_url, prev_counts)
            os.system("clear")
            print(output, end="")
            sys.stdout.flush()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n")
