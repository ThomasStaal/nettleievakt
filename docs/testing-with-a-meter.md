# First household test

Automated tests exercise synthetic sensor reports in real Home Assistant Core.
They do not verify a particular physical meter, firmware or household network.
Before calling a release stable, test it in a real installation.

## Record the setup

- Home Assistant and Nettleievakt versions.
- Meter and reader models, firmware and source integration.
- Units and meaning of the chosen energy/power sensors.
- Typical interval between source reports, including at low or zero import.
- The grid operator's calculation model and chosen warning target.

Keep addresses, serial numbers, access tokens and full configuration files private.

## Check the readings

1. Compare imported energy and current power with the source integration. Do not
   select export, one phase, solar production or an individual tariff register.
2. Add Nettleievakt during an hour. Confirm that the first partial hour is unknown.
3. Observe the following whole hour. Compare its imported kWh with the difference
   between the source meter readings at the two boundaries. Allow for report timing
   and the documented interpolation; investigate substantial differences.
4. Observe a normal change in household load. Confirm that the forecast responds.
   Do not deliberately overload equipment or use Nettleievakt as a safety limit.
5. Use a temporary warning target below the observed forecast to check the warning
   and notification blueprint. Restore the intended target afterwards.
6. Briefly disable the source integration. Confirm that incomplete/stale values
   become unknown and notifications do not report false safety. Re-enable it.
7. Restart Home Assistant. Confirm that saved daily peaks remain and the restart
   gap is not invented as zero consumption.
8. After at least three dates, check that the peak list contains distinct dates,
   not the three largest hours on one date. Compare with the operator's overview,
   remembering that earlier dates and gaps are absent from Nettleievakt.

## Report a discrepancy

Provide a short anonymised timeline with timestamps including UTC offset, units,
actual and expected values, and measurement coverage. Include whether the source
reset, went unavailable or changed units. These details are more useful than a
full database export and expose less household information.
