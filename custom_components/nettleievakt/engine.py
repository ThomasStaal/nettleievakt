"""Pure calculation engine. No Home Assistant, network or device access."""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from math import isfinite
from zoneinfo import ZoneInfo

OSLO = ZoneInfo("Europe/Oslo")
HOUR = 3600
RETENTION = 62 * 24 * HOUR
EPSILON = 0.001


def timestamp(value: datetime) -> float:
    """Never silently interpret a naive timestamp in the machine's time zone."""
    if value.tzinfo is None:
        raise ValueError("An aware timestamp is required")
    return value.timestamp()


def hour_start(ts: float) -> int:
    """Use UTC buckets: the two autumn 02:00 hours must remain distinct."""
    return int(ts // HOUR) * HOUR


@dataclass
class Hour:
    """Measured energy and observed seconds for one physical hour."""

    start: int
    kwh: float = 0.0
    seconds: float = 0.0

    @property
    def complete(self) -> bool:
        return abs(self.seconds - HOUR) <= EPSILON


class PeakTracker:
    """Aggregate cumulative import, never turn missing readings into zero."""

    def __init__(self, max_gap_seconds: float = 300) -> None:
        if not isfinite(max_gap_seconds) or not 30 <= max_gap_seconds <= 900:
            raise ValueError("Maximum gap must be between 30 and 900 seconds")
        self.max_gap = max_gap_seconds
        self.hours: dict[int, Hour] = {}
        self.last: tuple[float, float] | None = None

    def break_continuity(self) -> None:
        """Unknown/unavailable sources must not bridge an outage."""
        self.last = None

    def add(self, at: datetime, total_kwh: float) -> bool:
        """Ingest an actual source report, including freshly reported zero use."""
        ts = timestamp(at)
        if not isfinite(total_kwh) or total_kwh < 0:
            self.break_continuity()
            return False
        previous = self.last
        if previous is not None and ts <= previous[0]:
            return False
        self.last = (ts, total_kwh)
        self.hours = {key: val for key, val in self.hours.items() if key >= ts - RETENTION}
        if previous is None:
            return False
        start, old_total = previous
        elapsed = ts - start
        delta = total_kwh - old_total
        if delta < 0 or elapsed > self.max_gap:
            # A reset or a long gap establishes a new baseline, not a zero-use interval.
            return False
        cursor = start
        while cursor < ts:
            key = hour_start(cursor)
            stop = min(ts, key + HOUR)
            seconds = stop - cursor
            bucket = self.hours.setdefault(key, Hour(key))
            # A short interval straddling a boundary is split proportionally.
            bucket.kwh += delta * seconds / elapsed
            bucket.seconds += seconds
            cursor = stop
        return True

    def dump(self) -> dict:
        """Persist aggregates only; intentionally do not resume an old live baseline."""
        return {"hours": [asdict(hour) for _, hour in sorted(self.hours.items())]}

    def restore(self, data: dict, now: datetime) -> None:
        """Reject malformed storage rather than publishing corrupt peak estimates."""
        ts = timestamp(now)
        restored = {}
        for item in data.get("hours", []):
            hour = Hour(**item)
            if (
                not isinstance(hour.start, int)
                or hour.start % HOUR
                or not isfinite(hour.kwh)
                or hour.kwh < 0
                or not isfinite(hour.seconds)
                or not 0 <= hour.seconds <= HOUR + EPSILON
                or hour.start in restored
            ):
                raise ValueError("Invalid stored hour")
            if ts - RETENTION <= hour.start <= ts:
                restored[hour.start] = hour
        self.hours = restored
        self.last = None

    def snapshot(
        self,
        now: datetime,
        target_kw: float = 5.0,
        peak_days: int = 3,
        power_kw: float | None = None,
        power_at: datetime | None = None,
    ) -> dict:
        """Return provisional statistics, with explicit coverage and freshness."""
        if not isfinite(target_kw) or target_kw <= 0 or not 1 <= peak_days <= 5:
            raise ValueError("Invalid target or number of peak days")
        ts = timestamp(now)
        local = now.astimezone(OSLO)
        month_start = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_ts = month_start.timestamp()
        current_key = hour_start(ts)
        daily: dict[str, Hour] = {}
        observed = 0.0
        complete_hours = 0
        for key, hour in self.hours.items():
            if not month_ts <= key <= ts:
                continue
            observed += hour.seconds
            if not hour.complete or key + HOUR > ts:
                continue
            complete_hours += 1
            day = datetime.fromtimestamp(key, UTC).astimezone(OSLO).date().isoformat()
            if day not in daily or hour.kwh > daily[day].kwh:
                daily[day] = hour
        peaks = sorted(daily.items(), key=lambda item: (-item[1].kwh, item[0]))[:peak_days]
        peak_rows = [
            {
                "date": day,
                "hour": datetime.fromtimestamp(hour.start, UTC).astimezone(OSLO).isoformat(),
                "kw": round(hour.kwh, 4),
            }
            for day, hour in peaks
        ]
        monthly_peak = (
            sum(hour.kwh for _, hour in peaks) / peak_days if len(peaks) == peak_days else None
        )
        fresh = self.last is not None and 0 <= ts - self.last[0] <= self.max_gap
        current = self.hours.get(current_key, Hour(current_key))
        current_kwh = projection = remaining = None
        status = "waiting" if self.last is None else "stale"
        if fresh:
            assert self.last is not None
            measured_at = self.last[0]
            same_hour = hour_start(measured_at) == current_key
            covered_from_start = abs(current.seconds - (measured_at - current_key)) <= EPSILON
            status = "incomplete_hour"
            if same_hour and covered_from_start:
                status = "ok"
                current_kwh = current.kwh
                if (
                    power_kw is not None
                    and isfinite(power_kw)
                    and power_at is not None
                    and 0 <= ts - timestamp(power_at) <= self.max_gap
                ):
                    # Import-only energy cannot be reduced by exporting later in the hour.
                    projection = (
                        current.kwh + max(0, power_kw) * (current_key + HOUR - measured_at) / HOUR
                    )
                seconds_left = current_key + HOUR - measured_at
                remaining = max(0, target_kw - current.kwh) * HOUR / seconds_left
        return {
            "status": status,
            "current_hour_kwh": current_kwh,
            "projected_peak_kw": projection,
            "remaining_power_kw": remaining,
            "monthly_peak_kw": monthly_peak,
            "target_kw": target_kw,
            "hourly_target_risk": None if projection is None else projection >= target_kw,
            "top_days": peak_rows,
            "days_observed": len(daily),
            "complete_hours": complete_hours,
            "month_coverage_percent": min(100.0, 100 * observed / max(1, ts - month_ts)),
            "month": local.strftime("%Y-%m"),
            "last_measurement": (
                datetime.fromtimestamp(self.last[0], UTC).isoformat() if self.last else None
            ),
        }
