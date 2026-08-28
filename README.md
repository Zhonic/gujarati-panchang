# Gujarati Panchang → self-updating iPhone calendar

A GitHub Actions workflow computes a Gujarati panchang feed
(`docs/gujarati-panchang.ics`) and republishes it on a schedule. GitHub Pages
serves it over HTTPS, and iOS Calendar subscribes to that URL, so every day
shows the Gujarati month, paksha, tithi, nakshatra and Gujarati Samvat year with
no manual work after setup.

Each day is one all-day event, e.g. **`Shravan Sud Chaudas · VS 2082`**, with the
tithi end-time, nakshatra and both samvat years in the notes.

Tithi, month, and samvat are computed from the Swiss Ephemeris via the
[`drik-panchanga`](https://github.com/bdsatish/drik-panchanga) engine (the same
ephemeris drikpanchang.com uses), pinned to a fixed commit for reproducibility.

---

## What computes what

- `build_ics.py` — reads the engine and writes the `.ics`. No hardcoded dates;
  it always spans 5 days back to ~430 days ahead of the run date.
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

## Two things to know

**iOS refresh is not instant.** iOS refetches subscribed calendars on Apple's
schedule, not yours, sometimes only every several hours to daily. The file on
GitHub is always current; the delay is on the phone side and can't be forced.
You can lower the interval in some iOS versions under the subscription's
settings ("Fetch New Data"), but treat same-day-but-not-real-time as the
expectation.

**Validate before you rely on it.** Tithi is a lunar day whose boundaries can
fall near sunrise, so the *day a tithi is labelled on* can differ by one between
sources depending on location and sunrise. Before trusting this for
observances, spot-check ~5 dates (including an Ekadashi, Purnima, Amas and a
festival) against [drikpanchang.com](https://www.drikpanchang.com/gujarati/panchang/gujarati-day-panchang.html)
for the **same location** you configured. Verified against Drik for
Aug–Nov 2026 at Ahmedabad, including the Bestu Varas samvat rollover.

---

## Changing the reckoning location

Defaults use **Ahmedabad** sunrise (standard Gujarat panchang, matches Drik's
default, and what most of the diaspora follow for festival dates). To label days
by your **local** sunrise instead, edit the `env:` block in
`.github/workflows/panchang.yml`:

```yaml
  PANCHANG_LAT: "-38.1"     # Melbourne example
  PANCHANG_LON: "145.3"
  PANCHANG_TZ:  "10"        # or 11 during daylight saving
```

Timezone is a fixed offset, so local-sunrise reckoning drifts by an hour across
DST changes. Ahmedabad reckoning avoids that entirely, which is another reason
it's the default.

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
