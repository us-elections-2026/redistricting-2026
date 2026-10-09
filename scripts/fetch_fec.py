#!/usr/bin/env python3
"""추세 대상 구(data/states/*.json의 trend_districts)의 FEC 후보 모금 총액 → data/fec.json

사용법: export FEC_API_KEY=... ; python3 scripts/fetch_fec.py
"""
import glob
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date

ROOT = os.path.join(os.path.dirname(__file__), "..")
API = "https://api.open.fec.gov/v1"


def get(path, key, **p):
    p["api_key"] = key
    url = f"{API}{path}?{urllib.parse.urlencode(p)}"
    for i in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except Exception:  # noqa: BLE001  (간헐 429·5xx 재시도)
            if i == 2:
                raise
            time.sleep(5 * (i + 1))


def totals(st, dist, key):
    d = get("/candidates/totals/", key, office="H", state=st, district=dist, cycle=2026, election_year=2026,
            sort="-receipts", per_page=20, is_active_candidate="true")
    rows = []
    for c in d["results"]:
        if not c.get("receipts"):
            continue
        coh = c.get("cash_on_hand_end_period")
        rows.append({"name": c.get("name"), "party": (c.get("party") or "")[:3],
                     "receipts": round(float(c["receipts"]) / 1e6, 2),
                     "cash_on_hand": round(float(coh) / 1e6, 2) if coh is not None else None,
                     "coverage_end": (c.get("coverage_end_date") or "")[:10] or None})
    return rows


def targets():
    ds = set()
    for f in glob.glob(os.path.join(ROOT, "data", "states", "*.json")):
        s = json.load(open(f, encoding="utf-8"))
        ds |= set(s.get("trend_districts", []))
    return sorted(ds)


def main():
    key = os.environ.get("FEC_API_KEY", "DEMO_KEY")
    out = {"as_of": date.today().isoformat(),
           "source_label": "FEC (api.open.fec.gov) — 2026 사이클 후보 누적 모금·보유 현금, 단위 $M",
           "districts": {}}
    for k in targets():
        st, n = k.split("-")
        try:
            out["districts"][k] = totals(st, n, key)
            print(k, len(out["districts"][k]))
        except Exception as e:  # noqa: BLE001
            print(f"[warn] {k}: {e}", file=sys.stderr)
    json.dump(out, open(os.path.join(ROOT, "data", "fec.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
