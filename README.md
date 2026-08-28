# Gujarati Panchang → self-updating iPhone calendar

A GitHub Actions workflow computes a Gujarati panchang feed
(`docs/gujarati-panchang.ics`) and republishes it on a schedule. GitHub Pages
serves it over HTTPS, and iOS Calendar subscribes to that URL, so every day
shows the Gujarati month, paksha, tithi, nakshatra and Gujarati Samvat year with
no manual work after setup. Major Gujarati festivals appear as their own events
on top of the daily panchang.

Each day is one all-day event, e.g. **`Shravan Sud Chaudas · VS 2082`**, with the
tithi end-time, nakshatra and both samvat years in the notes. On a festival day,
a second all-day event carries the festival name, e.g. **`Diwali (Lakshmi Puja)`**.

Tithi, month, and samvat are computed from the Swiss Ephemeris via the
[`drik-panchanga`](https://github.com/bdsatish/drik-panchanga) engine (the same
ephemeris drikpanchang.com uses), pinned to a fixed commit for reproducibility.
Festival dates are **not** computed; they are curated in `festivals.csv` (see
[Festivals](#festivals) below).

---

## What computes what

- `build_ics.py` — reads the engine, loads `festivals.csv`, and writes the
  `.ics`. No hardcoded dates; it always spans 5 days back to ~430 days ahead of
  the run date.
- `festivals.csv` — hand-curated festival dates for Ahmedabad reckoning.
- `.github/workflows/panchang.yml` — installs `pyswisseph`, clones the pinned
  engine, runs the generator, and commits the feed only when it changes.
- `docs/gujarati-panchang.ics` — the published feed. A working copy is already
  committed, so the calendar works the moment Pages is on, before any Action.

---

## Setup, step by step

### 1. Create the repo
Put these files in a new **public** repo named e.g. `gujarati-panchang`.
(Public is required for free GitHub Pages. The feed contains only computed
dates, nothing private.)

```
build_ics.py
festivals.csv
docs/gujarati-panchang.ics
.github/workflows/panchang.yml
README.md
```

### 2. Turn on GitHub Pages
Repo **Settings → Pages**:
- **Source:** Deploy from a branch
- **Branch:** `main`, folder **`/docs`** → Save

After a minute the feed is live at:
```
https://<your-username>.github.io/gujarati-panchang/gujarati-panchang.ics
```
Open that URL in a browser once to confirm it downloads.

### 3. Let the Action write back to the repo
Repo **Settings → Actions → General → Workflow permissions** →
select **Read and write permissions** → Save. (This lets the weekly job commit
the refreshed feed.)

Trigger it once now: **Actions** tab → *Build Gujarati panchang feed* →
**Run workflow**. Confirm it finishes green.

### 4. Subscribe on iPhone
The reliable path is the URL subscription, not opening a downloaded file:

**Settings → Calendar → Accounts → Add Account → Other → Add Subscribed
Calendar**, then paste:
```
https://<your-username>.github.io/gujarati-panchang/gujarati-panchang.ics
```
Tap **Next → Save**. It appears as its own calendar named *Gujarati Panchang*.
(Tapping a `webcal://…` version of the same URL in Safari also works.)

Done. The Action keeps the file fresh; iOS refetches it on its own schedule.

---

## Festivals

Festival days appear as a second all-day event beside the daily panchang. The
set covers the major Gujarati observances: Uttarayan, Vasant Panchami, Maha
Shivratri, Holi, Ram Navami, Hanuman Jayanti, Akshaya Tritiya, Guru Purnima, Nag
Panchami, Raksha Bandhan, Krishna Janmashtami, Ganesh Chaturthi, Anant
Chaturdashi, Mahalaya Amavasya, all nine Navratri nights, Durgashtami, Dussehra,
Sharad Purnima, and the full Diwali cluster (Dhanteras, Kali Chaudas, Diwali,
Bestu Varas, Bhai Bij, Labh Pancham).

### Why festivals are curated, not computed

The panchang engine can generate festivals, but it approximates the time-of-day
rules real festivals use (pradosh, madhyahna, aparahna) with a sunrise rule, and
lands a day late on several majors (Diwali, Ganesh Chaturthi, Dussehra). A wrong
Diwali is worse than none, so festival dates live in a hand-verified file
instead. They are cross-checked against multiple panchang sources, several of
which reconcile against Drik Panchang.

### A quirk that is not a bug

A festival date will often **not match the daily tithi label on the same day**.
For example, on Diwali (8 Nov 2026) the daily event reads `Aaso Vad Chaudas`
while the festival event reads `Diwali (Lakshmi Puja)`. That is expected: the
daily line is the tithi at sunrise, while Diwali follows the evening (pradosh)
rule. Forcing them to agree would put the festival on the wrong day.

### Editing or adding a festival

`festivals.csv` is two columns, `date,name`, one row per occurrence:

```csv
date,name
2026-11-08,Diwali (Lakshmi Puja)
2026-10-18,Navratri Night 8 (Mahagauri)
2026-10-18,Durgashtami
```

- `date` is Gregorian `YYYY-MM-DD`. `name` is the label shown in the calendar.
- Several rows may share a date (e.g. a Navratri night and Durgashtami).
- Lines starting with `#`, blank lines, and the header are ignored. The comment
  block at the top records provenance and the dates still to be confirmed.
- A row dated beyond the ~430-day window is simply skipped until it comes into
  range, so it is safe to add future dates early.

After editing, commit the file; the next Action run (or a local rebuild)
regenerates the feed. No other change is needed.

### Dates to confirm with family

A few dates are genuine one-day splits between panchang sources, flagged in the
CSV header comments. Confirm these against your family / temple and edit the row
if needed:

- **Durgashtami 2026** — used 18 Oct (8th garba night); some place Ashtami puja 19 Oct.
- **Bestu Varas 2026** — used 10 Nov (matches the feed's Kartak Sud Ekam); some observe 9 Nov.
- **Uttarayan 2027** — used 14 Jan (Gujarat kite day); the astronomical Sankranti may be 15 Jan.
- **Maha Shivratri 2027** — used 6 Mar; some sources 7 Mar.
- **Sharad Purnima 2026, Guru Purnima 2027, Nag Panchami 2027** — lower confidence, verify when convenient.

### Yearly refresh

The CSV covers 2026–2027. Before the 2027 tail enters the window (aim for
mid-2027), append the next Gujarati year's rows, each verified against
drikpanchang.com for Ahmedabad. This is the one deliberate manual step; keeping
it manual is what prevents the wrong-Diwali risk that automatic computation
carries.

---

## Two things to know about the feed

**iOS refresh is not instant.** iOS refetches subscribed calendars on Apple's
schedule, not yours, sometimes only every several hours to daily. The file on
GitHub is always current; the delay is on the phone side and can't be forced.
Treat same-day-but-not-real-time as the expectation.

**Validate before you rely on it.** Tithi is a lunar day whose boundaries can
fall near sunrise, so the *day a tithi is labelled on* can differ by one between
sources depending on location and sunrise. Before trusting this for
observances, spot-check ~5 dates (an Agiyaras/Ekadashi, Punam, Amas, and a
festival) against [drikpanchang.com](https://www.drikpanchang.com/gujarati/panchang/gujarati-day-panchang.html)
for Ahmedabad. Verified against Drik for Aug–Nov 2026, including the Bestu Varas
samvat rollover.

---

## Reckoning location

Dates use **Ahmedabad** sunrise (`Asia/Kolkata`), the standard Gujarat panchang
and what the diaspora follows to stay in sync with India. India observes no
daylight saving, so the fixed offset is always correct.

Local-sunrise reckoning for another city is possible but not recommended: it
makes tithi labels diverge from India on roughly one day in five, which defeats
the purpose of staying in sync with family and community. If you ever do switch,
use an IANA timezone name (not a fixed hour offset) so daylight saving is
handled per date.

---

## Run it locally (optional)

```bash
pip install pyswisseph
git clone https://github.com/bdsatish/drik-panchanga.git engine
git -C engine checkout 6a251a7fb62d2b264e0fc8c8844f0c2e98f29d91
PYTHONPATH="$PWD/engine" python build_ics.py
open docs/gujarati-panchang.ics   # imports as a static copy, not a subscription
```

## Note on the engine's licence

`drik-panchanga` is AGPL-3.0-or-later. This setup clones it in CI and uses it to
compute data (panchang dates themselves aren't copyrightable), which is fine for
personal use. If you ever redistribute the engine or expose it as a network
service, review the AGPL terms first.
