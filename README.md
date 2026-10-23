# Nettleievakt

Local grid-tariff peak monitoring for Norwegian Home Assistant households.

Nettleievakt uses **existing Home Assistant sensors** to track hourly grid import,
show the highest daily peaks and warn when the current hour is heading above a
threshold you choose. It does not contact HomeWizard, Tibber or any other vendor.

**Early beta.** Automated calculation and integration tests are included. Physical
meter testing is still needed. Use this for visibility and notifications, not
electrical protection, billing or automatic control of critical equipment.

[Norsk brukerveiledning](docs/brukerveiledning.md) ·
[Calculation method](docs/calculations.md) ·
[First household test](docs/testing-with-a-meter.md) ·
[Report a problem](https://github.com/ThomasStaal/nettleievakt/issues)

## What you get

| Entity | What it tells you |
| --- | --- |
| Imported energy this hour | Imported kWh since the start of this clock hour, as of the latest measurement. |
| Projected hourly average | Estimated full-hour average if the latest power reading continues. |
| Remaining average power budget | Average import that would fit in the remaining hour under your chosen target. Not an electrical safety limit. |
| Observed monthly peak average | Average of the highest fully observed hour on each of the top three distinct local dates (configurable). |
| Hourly threshold warning | On when the projected hour reaches your target. Unknown when there is insufficient data. |
| Monthly measurement coverage | How much of the month so far has usable measurements. |
| Measurement status | Whether the current hour is covered, incomplete, stale or waiting for data. |

Example: after 30 minutes you have imported 2 kWh. If the current import of 8 kW
continues, the full hour would end at about 6 kWh, or an hourly average of 6 kW.
With a 5 kW target, the remaining half-hour budget is 6 kW on average. These are
estimates, not a recommendation to run equipment at that load.

## Requirements

- Home Assistant **2026.10 or newer**.
- A cumulative, whole-home **grid import** sensor in Wh, kWh or MWh, with
  `state_class: total` or `total_increasing`. Use a lifetime counter, not a daily
  utility meter, net-energy sensor, solar production or export counter.
- Regular source reports, preferably every few seconds. The default maximum
  accepted gap is five minutes. Hourly-only sources are not supported.
- Optional: a whole-home power sensor in W or kW. Import must be positive and
  export negative. Required for the forecast and warning.
- A grid tariff based on whole clock hours and the highest daily peaks on distinct
  dates. Check your operator's model; three days is a configurable default, not a
  universal rule.

With HomeWizard, first install the existing
[Home Assistant HomeWizard integration](https://www.home-assistant.io/integrations/homewizard/).
Select its combined imported-energy sensor, not one individual tariff register
or phase. Other integrations can work when they supply the same inputs; this is
not a claim that every meter or firmware has been hardware-tested.

## Install

### HACS custom repository

This project is not included in the default HACS catalogue.

1. In HACS, open the menu and choose **Custom repositories**.
2. Add `https://github.com/ThomasStaal/nettleievakt`, type **Integration**.
3. Download Nettleievakt. Enable pre-release versions if required for this beta.
4. Restart Home Assistant.
5. Open **Settings > Devices & services > Add integration > Nettleievakt**.
6. Choose your cumulative grid-import sensor, optionally the power sensor, and
   your hourly warning target. Leave a margin below the tariff boundary.

### Manual installation

Download the repository ZIP and copy only `custom_components/nettleievakt` into
your Home Assistant `config/custom_components` folder. The resulting path must be
`config/custom_components/nettleievakt/manifest.json`. Restart Home Assistant and
add the integration as described above. Do not install it in the Astro website.

The first partial hour is deliberately unknown. A monthly estimate appears only
after enough distinct dates have complete observed hours. Past measurements are
not imported from Recorder or the vendor's app in this version.

## Dashboard and notifications

The integration adds a device with six sensors and one binary sensor. Add them to
your dashboard using Home Assistant's card editor. No additional frontend plugin
is needed. The monthly-peak entity's `top_days` attribute shows the selected dates,
hours (including UTC offset) and values.

[Example dashboard YAML](examples/dashboard.yaml) is provided; replace the example
entity IDs with those in your installation. The names depend on your language and
the integration name.

For notifications, import [the notification blueprint](blueprints/hourly-warning.yaml)
into Home Assistant. Select the warning entity and your own notification action.
It waits two minutes before notifying, so brief spikes do not immediately alert.
A warning concerns this hour only, not a guaranteed increase in your monthly bill.

Change the warning threshold, number of peak days or accepted report gap under
the integration's **Configure** button. Changes retain existing hourly buckets.
Removing the integration deletes its own local history. Back it up first if needed.

## What this does not do

- No automatic load switching or EV-charge control.
- No tariff-price database or promised NOK savings.
- No retrospective import of vendor history.
- No attempt to reproduce a grid operator's validated billing data.
- No cloud account, telemetry, ads, affiliate links or external requests in the integration.

Missing periods can hide the month's largest peak. The observed peak average is
therefore always provisional. Check measurement coverage and compare with your
grid operator before drawing conclusions. A device or meter counter reset excludes
the affected interval. Restarts do not fill downtime with invented readings.

## Privacy and independence

Calculations run inside your Home Assistant installation. Hourly aggregates for
up to 62 days are stored locally in Home Assistant's `.storage` directory; normal
Home Assistant backups may include them. The source integrations retain their own
privacy settings and terms. Nettleievakt adds no cloud service and needs no API token.

Developed for [Praktiskinfo.no](https://praktiskinfo.no/). Some of our separate
hardware guides contain clearly labelled affiliate links, from which we may earn
commission. Using Nettleievakt requires no purchase through those links. This is
an independent project, not an official or vendor-endorsed HomeWizard product.

## Development

Core calculations can be tested on Python 3.12+:

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install pytest pytest-asyncio tzdata ruff pyyaml
python -m pytest tests/test_engine.py tests/test_metadata.py
ruff check .
ruff format --check .
```

Home Assistant integration tests use Linux and Python 3.14:

```sh
python -m pip install -r requirements-test.txt
python -m pytest tests/ha
```

The GitHub Actions workflow runs both suites. See
[the calculation notes](docs/calculations.md) before changing time handling or
missing-data behaviour. Report firmware, sensor units and anonymised timestamps
with issues; do not upload access tokens or your complete Home Assistant configuration.

## License

Our code is MIT licensed. This does not grant rights to any vendor API, trademark,
artwork or third-party integration. Their respective terms still apply.
