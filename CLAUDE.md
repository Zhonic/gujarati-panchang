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
  dates; the window is always 5 days back to ~430 days ahead of the run date.
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

The feed window reaches ~430 days ahead of the run date. `festivals.csv`
currently covers **VS 2082–2083 (2026–2027)**, through early November 2027. As
real time advances, the tail of the CSV moves inside the window and eventually
runs out; once the latest CSV date is fewer than ~430 days ahead of today, some
future days will have no festivals.

Task, to be done roughly once a year (target: before **mid-2027**, so the
2027–2028 rows exist well before the 2027 tail enters the window):

1. Determine the festival dates for the next Gujarati year (VS 2084 / 2028) for
   the same festival set already in the CSV.
2. Source each date by **verifying it against `drikpanchang.com`** (Gujarati day
   panchang, Ahmedabad / `Asia/Kolkata`). Drik is the authority. Do not compute
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

Several dates in the current CSV are genuine one-day source splits or
lower-confidence entries, listed in the CSV header comment block. When the owner
confirms the correct date with family / temple, edit the single CSV row and drop
that line from the header comment. Known flags at time of writing:

- `2026-10-18` Durgashtami — some panchangs place Ashtami puja `2026-10-19`.
- `2026-11-10` Bestu Varas — some families observe `2026-11-09`.
- `2027-01-14` Uttarayan — astronomical Makar Sankranti may be `2027-01-15`.
- `2027-03-06` Maha Shivratri — some sources `2027-03-07`.
- `2026-10-25` Sharad Purnima, `2027-07-18` Guru Purnima, `2027-08-22`
  Nag Panchami (Gujarat) — verify.

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
