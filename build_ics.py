#!/usr/bin/env python3
"""Generate a rolling Gujarati panchang .ics feed from the drik-panchanga engine.

Each Gregorian day becomes one all-day event whose title carries the Gujarati
month, paksha, tithi and Gujarati (Kartikadi) Samvat year. Tithi is computed at
sunrise for the configured place, so that place determines the day labels.

Configuration is read from environment variables so the GitHub Actions workflow
can override without editing code. Defaults reckon by Ahmedabad sunrise, which
matches the standard Gujarat panchang and Drik Panchang's default.
"""

import csv
import os
import re
from datetime import date, timedelta, datetime, timezone

import panchanga as P

# ---- Configuration -----------------------------------------------------
LAT = float(os.environ.get("PANCHANG_LAT", "23.0225"))       # Ahmedabad
LON = float(os.environ.get("PANCHANG_LON", "72.5714"))
TZ = float(os.environ.get("PANCHANG_TZ", "5.5"))
# Window spans 1 Jan of the run year through 31 Dec of the run year + YEARS_AHEAD.
YEARS_AHEAD = int(os.environ.get("PANCHANG_YEARS_AHEAD", "1"))
CAL_NAME = os.environ.get("PANCHANG_CAL_NAME", "Gujarati Panchang")
OUT_PATH = os.environ.get("PANCHANG_OUT", "docs/gujarati-panchang.ics")
FESTIVALS_CSV = os.environ.get("PANCHANG_FESTIVALS_CSV", "festivals.csv")
# Festival reminders: days before the festival, each firing at REMINDER_HOUR
# local time on the device. 0 is the on-day reminder. Daily events get none.
# The on-day reminder stays in the feed: Apple clients add their own default
# alert only to events with no VALARM, so it never doubles up.
REMINDER_DAYS = [int(x) for x in
                 os.environ.get("PANCHANG_REMINDER_DAYS", "30,7,1,0").split(",")
                 if x.strip()]
REMINDER_HOUR = int(os.environ.get("PANCHANG_REMINDER_HOUR", "9"))
# Festivals that get only the on-day reminder. Navratri nights 2-9 follow on
# from Night 1, whose advance reminders already cover the festival.
ON_DAY_ONLY = re.compile(r"^Navratri Night [2-9]\b")
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


def alarm_trigger(days_before, hour):
    """Return a TRIGGER duration firing at hour:00, days_before days ahead.

    All-day events start at local midnight, so the trigger is the signed
    offset from that midnight: 30 days before at 09:00 is -P29DT15H, and the
    same day at 09:00 is PT9H.
    """
    hours_before = days_before * 24 - hour
    if hours_before <= 0:
        return f"PT{-hours_before}H"
    days, hours = divmod(hours_before, 24)
    return "-P" + (f"{days}D" if days else "") + (f"T{hours}H" if hours else "")


def alarm_lines(name):
    """Return VALARM lines for a festival, one per configured reminder."""
    days = REMINDER_DAYS
    if ON_DAY_ONLY.match(name):
        days = [d for d in REMINDER_DAYS if d == 0]
    lines = []
    for days_before in days:
        when = {0: "today", 1: "tomorrow"}.get(days_before,
                                               f"in {days_before} days")
        lines += [
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            f"TRIGGER:{alarm_trigger(days_before, REMINDER_HOUR)}",
            fold(f"DESCRIPTION:{esc(f'{name} {when}')}"),
            "END:VALARM",
        ]
    return lines


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


def load_festivals(path):
    """Return a mapping of Gregorian date -> list of festival names.

    Reads a two-column CSV (date, name). Blank lines, lines beginning with
    ``#``, and the header row are skipped. A missing file yields an empty
    mapping so the feed degrades to panchang-only rather than failing.
    """
    festivals = {}
    if not os.path.exists(path):
        return festivals
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.reader(handle):
            if not row:
                continue
            first = row[0].strip()
            if not first or first.startswith("#") or first == "date":
                continue
            day = date.fromisoformat(first)
            festivals.setdefault(day, []).append(row[1].strip())
    return festivals


def slugify(name):
    """Reduce a festival name to a UID-safe token."""
    keep = [c.lower() if c.isalnum() else "-" for c in name]
    slug = "".join(keep)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def main():
    today = date.today()
    start = date(today.year, 1, 1)
    end = date(today.year + YEARS_AHEAD, 12, 31)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    festivals = load_festivals(FESTIVALS_CSV)

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
        for name in festivals.get(d, []):
            lines += [
                "BEGIN:VEVENT",
                f"UID:{d.isoformat()}-{slugify(name)}-fest@github-pages",
                f"DTSTAMP:{stamp}",
                f"DTSTART;VALUE=DATE:{d.strftime('%Y%m%d')}",
                f"DTEND;VALUE=DATE:{nxt.strftime('%Y%m%d')}",
                fold(f"SUMMARY:{esc(name)}"),
                "CATEGORIES:Festival",
                "TRANSP:TRANSPARENT",
                *alarm_lines(name),
                "END:VEVENT",
            ]
        count += 1
        d = nxt

    lines.append("END:VCALENDAR")

    out_dir = os.path.dirname(OUT_PATH)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    # newline="" keeps the explicit CRLFs intact on Windows (no \r\r\n).
    with open(OUT_PATH, "w", encoding="utf-8", newline="") as handle:
        handle.write("\r\n".join(lines) + "\r\n")
    print(f"Wrote {count} days to {OUT_PATH}")


if __name__ == "__main__":
    main()
