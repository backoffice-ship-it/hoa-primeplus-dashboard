#!/usr/bin/env python3
"""
HOA Prime+ — Nordpool BE Prijzen Scraper
Haalt dag-ahead prijzen op via de publieke Nordpool API
en slaat ze op als CSV in de /data map.

Wordt dagelijks uitgevoerd via GitHub Actions.
"""

import json
import csv
import os
import sys
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# ── Config ─────────────────────────────────────────────────────────────────────
OUTPUT_DIR  = os.path.join(os.path.dirname(__file__), "data")
TODAY_CSV   = os.path.join(OUTPUT_DIR, "today.csv")
TOMORROW_CSV= os.path.join(OUTPUT_DIR, "tomorrow.csv")
LATEST_JSON = os.path.join(OUTPUT_DIR, "latest.json")

# Nordpool publieke API endpoint (zelfde als dataportal gebruikt)
API_BASE = "https://dataportal-api.nordpoolgroup.com/api/DayAheadPrices"
HEADERS  = {
    "User-Agent":  "Mozilla/5.0 (compatible; HOA-Energy/1.0; +https://hoa.energy)",
    "Accept":      "application/json",
    "Origin":      "https://data.nordpoolgroup.com",
    "Referer":     "https://data.nordpoolgroup.com/",
}

# ── Fetch ───────────────────────────────────────────────────────────────────────
def fetch_nordpool(date_str: str) -> dict:
    """Haalt prijzen op voor een specifieke datum (YYYY-MM-DD) of 'latest'."""
    url = f"{API_BASE}?date={date_str}&market=DayAhead&deliveryArea=BE&currency=EUR"
    print(f"  → Ophalen: {url}")
    req = Request(url, headers=HEADERS)
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except HTTPError as e:
        print(f"  ✗ HTTP {e.code}: {e.reason}")
        raise
    except URLError as e:
        print(f"  ✗ URL fout: {e.reason}")
        raise

# ── Parse ───────────────────────────────────────────────────────────────────────
def parse_nordpool(data: dict, label: str) -> list[dict]:
    """
    Nordpool response structuur:
    {
      "multiAreaEntries": [
        {
          "deliveryStart": "2026-05-03T00:00:00Z",
          "deliveryEnd":   "2026-05-03T00:15:00Z",  (of 01:00:00 bij uurdata)
          "entryPerArea":  {"BE": 68.5, ...}
        },
        ...
      ]
    }
    """
    entries = data.get("multiAreaEntries", [])
    if not entries:
        # Alternatieve structuur proberen
        entries = data.get("data", data.get("rows", []))

    rows = []
    for entry in entries:
        # Timestamp
        ts_raw = (entry.get("deliveryStart")
               or entry.get("startTime")
               or entry.get("time")
               or entry.get("MTU"))
        if not ts_raw:
            continue

        # Prijs voor BE
        area_data = entry.get("entryPerArea", {})
        price_mwh = area_data.get("BE")
        if price_mwh is None:
            # Probeer andere structuren
            price_mwh = (entry.get("BE")
                      or entry.get("price")
                      or entry.get("value"))

        if price_mwh is None:
            continue

        try:
            price_mwh = float(str(price_mwh).replace(",", "."))
        except (ValueError, TypeError):
            continue

        # Parse timestamp naar CET
        try:
            if ts_raw.endswith("Z"):
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            else:
                ts = datetime.fromisoformat(ts_raw)
            # Naar CET (UTC+1 of UTC+2 zomertijd)
            ts_cet = ts.astimezone(timezone(timedelta(hours=2)))  # CEST
        except Exception:
            continue

        rows.append({
            "datum":      ts_cet.strftime("%Y-%m-%d"),
            "tijd":       ts_cet.strftime("%H:%M"),
            "uur":        ts_cet.hour,
            "kwartier":   ts_cet.minute,
            "eur_mwh":    round(price_mwh, 2),
            "eur_kwh":    round(price_mwh / 1000, 6),
            "label":      label,
            "timestamp":  ts_cet.isoformat(),
        })

    rows.sort(key=lambda r: r["timestamp"])
    return rows

# ── Write CSV ───────────────────────────────────────────────────────────────────
def write_csv(rows: list[dict], path: str):
    if not rows:
        print(f"  ⚠ Geen rijen om te schrijven naar {path}")
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fieldnames = ["datum","tijd","uur","kwartier","eur_mwh","eur_kwh","label","timestamp"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  ✓ {len(rows)} rijen → {path}")

# ── Write JSON summary ───────────────────────────────────────────────────────────
def write_summary(today_rows: list, tomorrow_rows: list):
    summary = {
        "gegenereerd":      datetime.now(timezone.utc).isoformat(),
        "vandaag_datum":    today_rows[0]["datum"] if today_rows else None,
        "morgen_datum":     tomorrow_rows[0]["datum"] if tomorrow_rows else None,
        "vandaag_slots":    len(today_rows),
        "morgen_slots":     len(tomorrow_rows),
        "vandaag_min":      min(r["eur_mwh"] for r in today_rows) if today_rows else None,
        "vandaag_max":      max(r["eur_mwh"] for r in today_rows) if today_rows else None,
        "vandaag_gem":      round(sum(r["eur_mwh"] for r in today_rows)/len(today_rows),2) if today_rows else None,
        "morgen_min":       min(r["eur_mwh"] for r in tomorrow_rows) if tomorrow_rows else None,
        "morgen_max":       max(r["eur_mwh"] for r in tomorrow_rows) if tomorrow_rows else None,
        "morgen_gem":       round(sum(r["eur_mwh"] for r in tomorrow_rows)/len(tomorrow_rows),2) if tomorrow_rows else None,
        "negatieve_uren":   len([r for r in today_rows if r["eur_mwh"] < 0]),
        "goedkope_uren":    len([r for r in today_rows if 0 <= r["eur_mwh"] < 30]),
    }
    with open(LATEST_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"  ✓ Samenvatting → {LATEST_JSON}")

# ── Main ─────────────────────────────────────────────────────────────────────────
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    today = datetime.now(timezone.utc)
    today_str    = today.strftime("%Y-%m-%d")
    tomorrow_str = (today + timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"\n{'='*55}")
    print(f"HOA Prime+ Nordpool Scraper — {today_str}")
    print(f"{'='*55}\n")

    # ── Vandaag ──
    print("📅 Vandaag ophalen…")
    today_rows = []
    try:
        data = fetch_nordpool(today_str)
        today_rows = parse_nordpool(data, "today")
        write_csv(today_rows, TODAY_CSV)
    except Exception as e:
        print(f"  ✗ Vandaag mislukt: {e}")

    # ── Morgen (day-ahead = "latest") ──
    print("\n📅 Morgen (day-ahead) ophalen…")
    tomorrow_rows = []
    try:
        data = fetch_nordpool("latest")
        tomorrow_rows = parse_nordpool(data, "tomorrow")
        # Controleer of het echt morgen is
        if tomorrow_rows and tomorrow_rows[0]["datum"] == today_str:
            print("  ℹ Day-ahead nog niet gepubliceerd (wordt rond 13u CET vrijgegeven)")
            tomorrow_rows = []
        else:
            write_csv(tomorrow_rows, TOMORROW_CSV)
    except Exception as e:
        print(f"  ✗ Morgen mislukt: {e}")
        # Leeg bestand aanmaken als placeholder
        write_csv([], TOMORROW_CSV)

    # ── Samenvatting ──
    print("\n📊 Samenvatting schrijven…")
    write_summary(today_rows, tomorrow_rows)

    print(f"\n{'='*55}")
    print("✅ Klaar!")
    if today_rows:
        print(f"   Vandaag: {len(today_rows)} slots · min {min(r['eur_mwh'] for r in today_rows)} · max {max(r['eur_mwh'] for r in today_rows)} €/MWh")
    if tomorrow_rows:
        print(f"   Morgen:  {len(tomorrow_rows)} slots · min {min(r['eur_mwh'] for r in tomorrow_rows)} · max {max(r['eur_mwh'] for r in tomorrow_rows)} €/MWh")
    print(f"{'='*55}\n")

    if not today_rows:
        sys.exit(1)

if __name__ == "__main__":
    main()
