# CLAUDE.md

Guidance for Claude Code working in this repository.

## What this repo is

A self-updating **Gujarati panchang** calendar. A GitHub Actions workflow runs
`build_ics.py`, which computes a rolling `.ics` feed
(`docs/gujarati-panchang.ics`). GitHub Pages serves that file over HTTPS and an
iPhone subscribes to the URL. Each day is one all-day event, e.g.
`Shravan Sud Chaudas · VS 2082`, carrying Gujarati month, paksha, tithi,
nakshatra and Gujarati Samvat.

Dates are computed from the Swiss Ephemeris via the
[`drik-panchanga`](https://github.com/bdsatish/drik-panchanga) engine, pinned to
a fixed commit.

## Layout

- `build_ics.py` — generator. Reads the engine, writes the feed. No hardcoded
  dates; the window is always 5 days back to ~430 days ahead of the run date.
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
  re-validate (see below) after any bump.
- **Reckoning is Ahmedabad** (`Asia/Kolkata`, fixed offset `5.5`; India has no
  DST, so a fixed offset is correct here). This is intentional: it keeps dates
  in sync with family and community in India. Do not switch the location. For a
  local-sunrise location, tithi labels diverge from India roughly one day in
  five, and a fixed offset would also drift across DST — a non-DST location like
  Ahmedabad sidesteps both.
- **Tithi is sunrise-based** and can differ from another panchang by one day at
  a tithi boundary. This is expected, not a bug. Validate against
  `drikpanchang.com` for the same location rather than "fixing" it.
- **Gujarati Samvat rule:** `= Chaitradi Vikram − 1` for masa 1..7
  (Chaitra..Aaso), else equal. Verified at Bestu Varas 2026: Aaso Vad Amas
  (9 Nov, VS 2082) → Kartak Sud Ekam (10 Nov, VS 2083). Do not change without
  re-checking this rollover.
- **ICS correctness:** CRLF line endings, RFC 5545 folding at 74 octets, and
  property escaping are already handled in `build_ics.py` — preserve them.
  All-day events use `DTSTART;VALUE=DATE`. Keep the feed free of hardcoded
  dates; derive the window from the run date.
- **CI actions are pinned** to `actions/checkout@v5` and
  `actions/setup-python@v6` (Node 24). Do not downgrade.
- **iOS refresh latency is not controllable.** Do not add hacks that claim to
  force it; the file is fresh, the phone refetches on Apple's own schedule.
- **Engine licence is AGPL-3.0-or-later.** Clone-and-compute in CI only; do not
  vendor its source into this repo.

## Coding conventions

- Python docstrings and comments describe the code itself; no second-person
  pronouns ("you"/"your") in docstrings or comments.
- Generator dependencies stay minimal: standard library plus `pyswisseph` (and
  the cloned engine). Do not add heavy dependencies.
- Output must be deterministic for a given run date.

## Task: add curated festivals

Festivals are wanted (Diwali, Janmashtami, Navratri/Dussehra, Ganesh Chaturthi,
Uttarayan, etc.), currently absent.

### Why not compute them from the engine

The engine's festival selector approximates time-of-day rules (pradosh,
madhyahna, aparahna) with sunrise rules and lands **a day late on several
majors**. Confirmed wrong values from the engine, for Ahmedabad:

- Diwali → 9 Nov 2026 (correct: **8 Nov 2026**)
- Ganesh Chaturthi → 15 Sep 2026 (correct: **14 Sep 2026**)
- Dussehra → 21 Oct 2026 (correct: **20 Oct 2026**)

A wrong Diwali is worse than no festivals. **Do not compute festival dates from
the engine.** Use a curated, human-verified list.

### Design

1. Add `festivals.csv` with two columns: `date` (Gregorian `YYYY-MM-DD`) and
   `name`. One row per occurrence.
2. In `build_ics.py`, add a loader that reads `festivals.csv` and, for each row
   whose date falls inside the feed window, emits a **separate** all-day
   `VEVENT`: `CATEGORIES:Festival`, a stable UID like
   `{date}-{slug}-fest@github-pages`, `SUMMARY` = the festival name. Leave the
   daily panchang events unchanged. If `festivals.csv` is absent, emit no
   festival events and do not error.
3. Keep it deterministic and window-bounded: never emit a festival dated outside
   the generated range.

### Sourcing discipline (the important part)

Populate `festivals.csv` by verifying **each** date against
`drikpanchang.com` (Gujarati day panchang, Ahmedabad). Drik is the authority
here. Do not trust generic date-aggregator sites, and do not back-fill from the
engine. Web-search to confirm, and if a date cannot be verified, leave it out
and note it rather than guessing.

Use these confirmed values as acceptance checks — if the CSV disagrees with any
of them, the CSV is wrong:

- Diwali 2026 = `2026-11-08`
- Ganesh Chaturthi 2026 = `2026-09-14`
- Dussehra (Vijayadashami) 2026 = `2026-10-20`

Festival set to include (Gujarati labels): Makar Sankranti (Uttarayan), Vasant
Panchami, Maha Shivratri, Holi (Holika Dahan), Ram Navami, Hanuman Jayanti,
Akshaya Tritiya, Guru Purnima, Nag Panchami, Raksha Bandhan, Krishna
Janmashtami, Ganesh Chaturthi, Anant Chaturdashi, Mahalaya Amavasya (Shraddh),
Durgashtami, Navratri start, Dussehra (Vijayadashami), Dhanteras, Kali Chaudas,
Diwali, Bestu Varas (Gujarati New Year), Labh Pancham, Vaikuntha Ekadashi.

Seed the file for **VS 2082–2083 (Gregorian 2026–2027)** so it covers the whole
~14-month window. Refresh yearly by appending the next year's verified rows;
this is the one manual step and it is intentional (correctness over automation
for religious dates).

### Acceptance criteria

- Feed still parses with `icalendar`.
- Festival events appear only within the generated window.
- The three confirmed anchors above land exactly.
- No festival date is engine-computed.
- Daily panchang events are unchanged.
- Local run and CI both succeed.

## Validation checklist (run after any change)

1. Local run produces `docs/gujarati-panchang.ics` without error.
2. The file parses with `icalendar`.
3. Spot-check ~5 daily dates (an Agiyaras/Ekadashi, Punam, Amas, plus a
   festival) against `drikpanchang.com` for Ahmedabad.
4. Bestu Varas rollover still reads VS 2082 → 2083 across 9–10 Nov 2026.
