#!/usr/bin/env python3
"""Generate a rolling Gujarati panchang .ics feed from the drik-panchanga engine.

Each Gregorian day becomes one all-day event whose title carries the Gujarati
month, paksha, tithi and Gujarati (Kartikadi) Samvat year. Tithi is computed at
sunrise for the configured place, so that place determines the day labels.

Configuration is read from environment variables so the GitHub Actions workflow
can override without editing code. Defaults reckon by Ahmedabad sunrise, which
matches the standard Gujarat panchang and Drik Panchang's default.
"""

import os
from datetime import date, timedelta, datetime, timezone

import panchanga as P

# ---- Configuration -----------------------------------------------------
LAT = float(os.environ.get("PANCHANG_LAT", "23.0225"))       # Ahmedabad
LON = float(os.environ.get("PANCHANG_LON", "72.5714"))
TZ = float(os.environ.get("PANCHANG_TZ", "5.5"))
DAYS_AHEAD = int(os.environ.get("PANCHANG_DAYS_AHEAD", "430"))
DAYS_BACK = int(os.environ.get("PANCHANG_DAYS_BACK", "5"))
CAL_NAME = os.environ.get("PANCHANG_CAL_NAME", "Gujarati Panchang")
OUT_PATH = os.environ.get("PANCHANG_OUT", "docs/gujarati-panchang.ics")
# ------------------------------------------------------------------------

PLACE = P.Place(LAT, LON, TZ)

MASA = ["", "Chaitra", "Vaishakh", "Jeth", "Ashadh", "Shravan", "Bhadarvo",
        "Aaso", "Kartak", "Magshar", "Posh", "Maha", "Fagan"]

# Index 1..15 = Sud (Shukla) tithis, 16..30 = Vad (Krishna) tithis.
TITHI = ["", "Ekam", "Bij", "Trij", "Choth", "Pancham", "Chhath", "Satam",
         "Aatham", "Nom", "Dasam", "Agiyaras", "Baras", "Teras", "Chaudas",
         "Punam", "Ekam", "Bij", "Trij", "Choth", "Pancham", "Chhath", "Satam",
         "Aatham", "Nom", "Dasam", "Agiyaras", "Baras", "Teras", "Chaudas", "Amas"]

NAK = ["", "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashirsha", "Ardra",
       "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
       "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
       "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
       "Dhanishtha", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
       "Revati"]


def gujarati_samvat(vikram_chaitradi, masa_num):
    """Convert North (Chaitradi) Vikram year to the Gujarati (Kartikadi) year.

    The Gujarati year turns over at Kartak (masa 8, Bestu Varas). For the
    months Chaitra..Aaso (1..7) it trails the Chaitradi Vikram year by one.
    """
    return vikram_chaitradi - 1 if 1 <= masa_num <= 7 else vikram_chaitradi


def fold(line):
    """Fold a content line to 74 octets per RFC 5545, splitting on byte width."""
    out = []
    while len(line.encode("utf-8")) > 74:
        cut = 74
        while len(line[:cut].encode("utf-8")) > 74:
            cut -= 1
        out.append(line[:cut])
        line = " " + line[cut:]
    out.append(line)
    return "\r\n".join(out)


def esc(text):
    """Escape a text value for an iCalendar property per RFC 5545."""
    return (text.replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace("\n", "\\n"))


def day_record(d):
    """Return (summary, description) strings for one Gregorian date."""
    jd = P.gregorian_to_jd(P.Date(d.year, d.month, d.day))
    tt = P.tithi(jd, PLACE)
    ti = tt[0]
    end_h, end_m = int(tt[1][0]), int(tt[1][1])
    ti_end = f"{end_h % 24:02d}:{end_m:02d}"
    m, is_adhika = P.masa(jd, PLACE, amanta=True)
    _, _, vikram = P.elapsed_year(jd, m)
    nk = P.nakshatra(jd, PLACE)[0]
    gs = gujarati_samvat(vikram, m)
    paksha = "Sud" if ti <= 15 else "Vad"
    masa_label = MASA[m] + (" (Adhik)" if is_adhika else "")
    summary = f"{masa_label} {paksha} {TITHI[ti]} \u00b7 VS {gs}"
    description = (f"Tithi: {paksha} {TITHI[ti]} (ends {ti_end} local)\n"
                   f"Month: {masa_label} (amanta)\n"
                   f"Nakshatra: {NAK[nk]}\n"
                   f"Gujarati Samvat: {gs}  |  Vikram (Chaitradi): {vikram}")
    return summary, description


def main():
    today = date.today()
    start = today - timedelta(days=DAYS_BACK)
    end = today + timedelta(days=DAYS_AHEAD)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0",
        "PRODID:-//gujarati-panchang//drik-panchanga//EN",
        "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
        f"X-WR-CALNAME:{esc(CAL_NAME)}",
        "X-WR-TIMEZONE:UTC",
        "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
        "X-PUBLISHED-TTL:PT12H",
    ]

    count = 0
    d = start
    while d <= end:
        summary, description = day_record(d)
        nxt = d + timedelta(days=1)
        uid = f"{d.isoformat()}-guj-panchang@github-pages"
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{d.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{nxt.strftime('%Y%m%d')}",
            fold(f"SUMMARY:{esc(summary)}"),
            fold(f"DESCRIPTION:{esc(description)}"),
            "TRANSP:TRANSPARENT",
            "END:VEVENT",
        ]
        count += 1
        d = nxt

    lines.append("END:VCALENDAR")

    out_dir = os.path.dirname(OUT_PATH)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as handle:
        handle.write("\r\n".join(lines) + "\r\n")
    print(f"Wrote {count} days to {OUT_PATH}")


if __name__ == "__main__":
    main()
