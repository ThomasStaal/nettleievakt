# Calculation contract

## Input

Use a nonnegative cumulative grid-import meter. Units Wh, kWh and MWh are
normalised to kWh. Signed whole-home power in W or kW is optional. Net cumulative
energy, individual phases, tariff-specific registers and resetting daily counters
are not suitable inputs. The setup form validates units and state class, but cannot
infer the meaning of an arbitrarily named sensor: the user must select import.

## Time and aggregation

Hourly buckets use UTC epoch boundaries. Norway's local clock hours align with
these boundaries. Local dates and months use Europe/Oslo, regardless of the host
computer's timezone. The autumn repeated hour has two separate UTC buckets; the
spring missing hour is not invented. A Norwegian calendar month can therefore
contain a different number of physical hours than calendar days multiplied by 24.

For successive reports at t0 and t1, imported energy is E(t1) - E(t0). Intervals
crossing an hour boundary are split proportionally by elapsed seconds. This assumes
uniform consumption over that short interval, so boundary estimates are not
identical to the grid operator's meter readings. Reports can arrive more frequently
than Home Assistant state changes. A timer reads `last_reported` to distinguish
fresh, unchanged reports from stale cached values.

An hour participates in peak calculations only when all 3,600 seconds are covered
by accepted intervals. Every local date contributes at most one completed-hour
maximum. The monthly estimate averages the largest N distinct-day maxima, with
N configurable from 1 to 5 (default 3). Until N dates are observed, the estimate
is unknown, not padded with zeroes. The current unfinished hour is excluded.

## Missing data

- NaN, infinity, negative imported energy and unavailable states break continuity.
- Counter decreases establish a new baseline; the reset interval is excluded.
- Intervals exceeding the configured maximum gap are excluded completely.
- Out-of-order and duplicate timestamps are ignored without changing the baseline.
- Restart restores hourly aggregates, but not the previous live baseline.
- History is bounded to 62 days and is deleted when the config entry is removed.

Coverage equals accepted seconds in the current local month divided by elapsed
physical seconds since local midnight on the first day. It is not a confidence
interval. Even a small missing period may hide the actual largest peak. The
observed monthly average is always provisional and is not a billing guarantee.
The software cannot detect a plausible-looking positive jump in a faulty counter;
check the underlying sensor when a peak looks wrong.

## Forecast

Let E be imported kWh from the current hour's start through the latest energy
report, R the seconds from that report to the hour's end, and P the latest import
power in kW (negative/export is clamped to zero):

```text
projected full-hour average (kW) = E + max(0, P) * R / 3600
remaining average power budget (kW) = max(0, target - E) * 3600 / R
```

The forecast assumes the latest power also applies between the energy report and
now. It is withheld if either source is stale, has a future timestamp, or current
hour coverage is incomplete. A first report exactly at the hour boundary can
establish a valid zero-duration baseline.

The warning is `projected >= target`, without rounding beforehand. It concerns a
chosen hourly target, not the final monthly band. Remaining power budget is not a
fuse rating, load-control instruction or safe operating limit. No tariff prices or
financial savings are calculated in this beta.

## References

- [Elvia: highest hourly peaks on three distinct dates](https://www.elvia.no/nettleie/alt-om-nettleiepriser/slik-fungerer-fastleddet/)
- [Lnett: tariff structure](https://www.l-nett.no/nettleie/priser-og-vilkar-privat/)
- [Home Assistant: HomeWizard sensor meanings](https://www.home-assistant.io/integrations/homewizard/)
- [HomeWizard: API scope and terms](https://api-documentation.homewizard.com/docs/introduction/)

Reviewed 23 October 2026. Providers may use different models; no operator is
automatically selected or represented by this integration.
