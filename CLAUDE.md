# CLAUDE.md

Guidance for Claude Code working in this repository.

## What this repo is

A self-updating **Gujarati panchang** calendar. A GitHub Actions workflow runs
`build_ics.py`, which computes a rolling `.ics` feed
(`docs/gujarati-panchang.ics`). GitHub Pages serves that file over HTTPS and an
iPhone subscribes to the URL. Each day is one all-day event, e.g.
`Shravan Sud Chaudas · VS 2082`, carrying Gujarati month, paksha, tithi,
nakshatra and Gujarati Samvat. Festival days get an additional all-day event.

Panchang dates are computed from the Swiss Ephemeris via the
[`drik-panchanga`](https://github.com/bdsatish/drik-panchanga) engine, pinned to
a fixed commit. Festival dates are **not** computed; they come from a curated
CSV (see below).

## Layout

- `build_ics.py` — generator. Reads the engine, writes the feed. No hardcoded
  dates; the window is always 1 Jan of the run year through 31 Dec of the
  following year (`PANCHANG_YEARS_AHEAD`, default 1).
- `festivals.csv` — curated festival dates (`date,name`), Ahmedabad reckoning.
  The generator loads this and emits one extra all-day event per row that falls
  inside the window.
- `.github/workflows/panchang.yml` — CI. Installs `pyswisseph`, clones the
  pinned engine, runs the generator, commits the feed when it changes.
- `docs/gujarati-panchang.ics` — the published feed (a working copy is committed
  so the calendar works before the first Action run).
- `requirements.txt` — `pyswisseph` only.

## Run and test locally

```bash
pip install pyswisseph
git clone https://github.com/bdsatish/drik-panchanga.git engine
git -C engine checkout 6a251a7fb62d2b264e0fc8c8844f0c2e98f29d91
PYTHONPATH="$PWD/engine" python build_ics.py
```

After any change, parse the output before committing:

```bash
python -c "from icalendar import Calendar; \
Calendar.from_ical(open('docs/gujarati-panchang.ics','rb').read()); print('ok')"
```

## Hard constraints — do not violate

- **Engine is pinned. Never `pip install drik-panchanga`.** The PyPI build
  (0.1.0) is stale and has a different API — its `elapsed_year` returns two
  values instead of three and breaks this code. Always clone the GitHub repo at
  the SHA in the workflow (`PANCHANGA_REF`). Bump the SHA only deliberately, and
  re-validate after any bump.
- **Reckoning is Ahmedabad** (`Asia/Kolkata`, fixed offset `5.5`; India has no
  DST, so a fixed offset is correct here). This is intentional: it keeps dates
  in sync with family and community in India. Do not switch the location. For a
  local-sunrise location, tithi labels diverge from India roughly one day in
  five, and a fixed offset would also drift across DST.
- **Never compute festival dates from the engine.** Its festival selector
  approximates time-of-day rules (pradosh / madhyahna / aparahna) with sunrise
  rules and lands a day late on several majors (verified wrong: Diwali,
  Ganesh Chaturthi, Dussehra). Festivals come only from `festivals.csv`.
- **Festival dates intentionally differ from the daily tithi label** on the same
  day, because festivals follow evening/midnight rules while the daily line is
  the tithi at sunrise. Example: on Diwali (8 Nov 2026) the daily event reads
  `Aaso Vad Chaudas` while the festival event reads `Diwali`. This is correct,
  not a bug. Do not "align" them.
- **Tithi is sunrise-based** and can differ from another panchang by one day at
  a boundary. Validate against `drikpanchang.com` for Ahmedabad rather than
  "fixing" it.
- **Gujarati Samvat rule:** `= Chaitradi Vikram − 1` for masa 1..7
  (Chaitra..Aaso), else equal. Verified at Bestu Varas 2026
  (Amas → Kartak Sud Ekam across 9–10 Nov 2026). Do not change without
  re-checking that rollover.
- **ICS correctness:** CRLF line endings, RFC 5545 folding at 74 octets, and
  property escaping are already handled — preserve them. All-day events use
  `DTSTART;VALUE=DATE`. Keep the feed free of hardcoded dates.
- **CI actions are pinned** to `actions/checkout@v5` and
  `actions/setup-python@v6` (Node 24). Do not downgrade.
- **Festival reminders are VALARMs on festival events only** (never on the
  daily panchang events). Defaults: 30, 7, 1 and 0 days before at 09:00 device
  local time (`PANCHANG_REMINDER_DAYS`, `PANCHANG_REMINDER_HOUR`). Triggers are
  relative to the all-day start (local midnight), e.g. `-P29DT15H`, `PT9H`.
  Navratri Nights 2–9 get only the on-day reminder (`ON_DAY_ONLY`). iOS only
  fires them when "Remove Alerts" is off on the subscription. **Keep the on-day
  (`0`) reminder in the feed:** Apple clients add the device's default alert
  only to events with no VALARM (CalDAV default-alarm rule), so dropping it
  would leave festivals with no on-day alert rather than avoid a duplicate.
- **iOS refresh latency is not controllable.** Do not add hacks that claim to
  force it.
- **Engine licence is AGPL-3.0-or-later.** Clone-and-compute in CI only; do not
  vendor its source into this repo.

## Coding conventions

- Python docstrings and comments describe the code itself; no second-person
  pronouns ("you"/"your") in docstrings or comments.
- Generator dependencies stay minimal: standard library plus `pyswisseph` (and
  the cloned engine). Do not add heavy dependencies.
- Output must be deterministic for a given run date.

## `festivals.csv` format

- Two columns: `date` (Gregorian `YYYY-MM-DD`) and `name`.
- One row per occurrence. A day may have several rows (e.g. a Navratri night and
  Durgashtami on the same date).
- Lines beginning with `#`, blank lines, and the `date` header are ignored. The
  header comment block records provenance and the dates still needing
  verification.
- The loader emits a row only if its date is inside the generated window, so
  future-dated rows sitting past the horizon are harmless and simply wait.

## To-Do: festival maintenance

The festival feature is **built and working**. What remains is upkeep, not
construction. There are two recurring jobs.

### To-Do 1 — Yearly refresh (append the next year before the horizon runs out)

The feed window spans 1 Jan of the run year through 31 Dec of the following
year, and jumps forward a full year on 1 January. `festivals.csv` currently
covers the full calendar years **2026, 2027 and 2028** (VS 2082–2085). On
1 Jan 2028 the window becomes 2028–2029, so any 2029 festival missing from the
CSV shows up as a gap immediately.

Task, to be done once a year (target: before **31 December** of each year, so
the year-after-next rows exist before the window rolls; next deadline
**end of 2027**, for the 2029 rows):

1. Determine the festival dates for the next calendar year (2029) for the same
   festival set already in the CSV.
2. Source each date by **verifying it against `drikpanchang.com`**: the Gujarati
   calendar page for Ahmedabad,
   `https://www.drikpanchang.com/gujarati/calendar/gujarati-calendar.html?geoname-id=1279233&year=YYYY`.
   Its HTML lists each festival as `dpEventName` / `dpEventGregDate`, so parse
   the raw page rather than trusting a summariser. Navratri Night N is Drik's
   "Navratri Day N" from
   `https://www.drikpanchang.com/navratri/ashwin-shardiya-navratri-dates.html?year=YYYY&geoname-id=1279233`.
   Drik is the authority. Do not compute
   from the engine, and do not trust generic aggregator sites. Web-search to
   corroborate; if a date cannot be verified, leave it out and note it rather
   than guessing.
3. Append the new rows to `festivals.csv` (keep existing rows; order is not
   significant). Update the header comment block with any new
   confirm-with-family items.
4. Regenerate and parse-check the feed.

Acceptance for the refresh:

- Feed still parses with `icalendar`.
- The new year's Diwali, Ganesh Chaturthi and Dussehra match Drik for Ahmedabad
  (these three are the boundary-sensitive tripwires — if any is off, the batch
  is wrong).
- Navratri appears as nine consecutive night rows plus a separate Durgashtami
  and Dussehra, matching the existing pattern.
- No festival date was engine-computed.

### To-Do 2 — Lock the flagged dates

Several dates in the current CSV are genuine one-day source splits, listed in
the CSV header comment block. Every row has been checked against Drik for
Ahmedabad; the flags are where family tradition or other panchangs may differ.
When the owner confirms the correct date with family / temple, edit the single
CSV row and drop that line from the header comment. Known flags at time of
writing:

- `2026-10-18` Durgashtami — the 8th garba night; Drik places Durga Ashtami on
  `2026-10-19`. Deliberately kept off-Drik pending family confirmation.
- `2026-11-10` Bestu Varas — matches Drik; some families observe `2026-11-09`.
- `2027-01-14` Uttarayan — Gujarat kite day; Drik Makar Sankranti is
  `2027-01-15`. Deliberately kept off-Drik pending family confirmation.
- `2028-01-15` Uttarayan — Drik date; the kite day may be kept on `2028-01-14`.
- `2026-03-26`, `2028-04-03` Ram Navami — Drik Smarta date; the Vaishnava
  (ISKCON) date is the next day.
- `2027-03-21` Holika Dahan / `2027-03-22` Dhuleti — Drik; a minority of
  panchangs move both a day later.
- `2027-10-14` Sharad Purnima — Drik; some sources `2027-10-15`.
- `2028-09-27` Navratri Night 9 — Drik's Day 9 shares the date with Dussehra
  (Ashtami and Navami both fall on `2028-09-26`); garba may end on the 26th.

Do not silently change a flagged date without a source; either verify it against
Drik / the owner's tradition, or leave it and keep the flag.

## Validation checklist (run after any change)

1. Local run produces `docs/gujarati-panchang.ics` without error.
2. The file parses with `icalendar`.
3. Spot-check ~5 daily dates (an Agiyaras/Ekadashi, Punam, Amas, plus a
   festival) against `drikpanchang.com` for Ahmedabad.
4. Diwali / Ganesh Chaturthi / Dussehra festival rows match Drik for the years
   in the CSV.
5. Bestu Varas rollover still reads VS 2082 → 2083 across 9–10 Nov 2026.
