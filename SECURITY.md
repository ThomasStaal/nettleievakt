# Security and privacy

Nettleievakt reads selected Home Assistant sensor states and stores hourly
aggregates locally. It opens no network listener, makes no outbound requests and
does not control electrical equipment. It requires no vendor token.

Home Assistant configuration backups may contain the local aggregate history.
Remove household consumption, locations and identifying sensor names before
sharing diagnostics. Never post access tokens or `secrets.yaml` in an issue.

Report security problems privately to post@norbin.no with the version and a
minimal reproduction. Do not publicly disclose exploitable details before a fix
has been discussed. This beta has no response-time or availability guarantee.
