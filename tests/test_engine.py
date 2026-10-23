"""Calculation tests run without Home Assistant or physical hardware."""

import importlib.util
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location(
    "peak_engine", ROOT / "custom_components/nettleievakt/engine.py"
)
engine = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = engine
spec.loader.exec_module(engine)
PeakTracker = engine.PeakTracker


def at(text):
    return datetime.fromisoformat(text)


def fill(tracker, start, hours, kw=2, total=0):
    tracker.add(start, total)
    for minute in range(1, hours * 60 + 1):
        tracker.add(start + timedelta(minutes=minute), total + kw * minute / 60)
    return start + timedelta(hours=hours)


def test_empty_does_not_claim_zero_or_three_days():
    data = PeakTracker().snapshot(at("2026-10-01T00:00:00+02:00"))
    assert data["status"] == "waiting"
    assert data["monthly_peak_kw"] is None
    assert data["current_hour_kwh"] is None
    assert data["hourly_target_risk"] is None
    assert data["month_coverage_percent"] == 0


def test_hour_and_projection_use_energy_not_instantaneous_peak():
    tracker = PeakTracker()
    start = at("2026-10-01T10:00:00+02:00")
    for minute in range(31):
        tracker.add(start + timedelta(minutes=minute), 100 + minute / 15)
    now = start + timedelta(minutes=30)
    data = tracker.snapshot(now, power_kw=8, power_at=now)
    assert data["current_hour_kwh"] == pytest.approx(2)
    assert data["projected_peak_kw"] == pytest.approx(6)
    assert data["remaining_power_kw"] == pytest.approx(6)
    assert data["hourly_target_risk"] is True


def test_no_power_means_no_forecast_but_energy_still_works():
    tracker = PeakTracker()
    start = at("2026-10-01T10:00:00+02:00")
    tracker.add(start, 0)
    tracker.add(start + timedelta(minutes=1), 0.1)
    data = tracker.snapshot(start + timedelta(minutes=1))
    assert data["current_hour_kwh"] == pytest.approx(0.1)
    assert data["projected_peak_kw"] is None
    assert data["hourly_target_risk"] is None


def test_export_cannot_cancel_already_imported_energy():
    tracker = PeakTracker()
    now = fill(tracker, at("2026-10-01T10:00:00+02:00"), 1)
    tracker.add(now + timedelta(minutes=1), 2.2)
    data = tracker.snapshot(now + timedelta(minutes=1), power_kw=-4, power_at=now)
    assert data["projected_peak_kw"] == pytest.approx(0.2)


def test_late_install_waits_for_next_full_hour():
    tracker = PeakTracker()
    start = at("2026-10-01T10:30:00+02:00")
    end = fill(tracker, start, 2)
    data = tracker.snapshot(end, peak_days=1)
    assert data["complete_hours"] == 1
    assert data["monthly_peak_kw"] == pytest.approx(2)
    assert data["current_hour_kwh"] == pytest.approx(1)


def test_gap_is_not_spread_across_hours():
    tracker = PeakTracker()
    tracker.add(at("2026-10-01T10:00:00+02:00"), 100)
    tracker.add(at("2026-10-01T11:00:00+02:00"), 112)
    assert not tracker.hours
    assert tracker.snapshot(at("2026-10-01T11:00:00+02:00"))["monthly_peak_kw"] is None


def test_counter_reset_does_not_create_negative_energy_or_complete_hour():
    tracker = PeakTracker()
    start = at("2026-10-01T10:00:00+02:00")
    tracker.add(start, 100)
    tracker.add(start + timedelta(minutes=1), 100.1)
    tracker.add(start + timedelta(minutes=2), 0)
    tracker.add(start + timedelta(minutes=3), 0.1)
    data = tracker.snapshot(start + timedelta(minutes=3))
    assert data["status"] == "incomplete_hour"
    assert data["current_hour_kwh"] is None
    assert sum(h.kwh for h in tracker.hours.values()) == pytest.approx(0.2)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1])
def test_invalid_values_break_continuity(bad):
    tracker = PeakTracker()
    start = at("2026-10-01T10:00:00+02:00")
    tracker.add(start, 0)
    assert not tracker.add(start + timedelta(minutes=1), bad)
    assert tracker.last is None
    tracker.add(start + timedelta(minutes=2), 2)
    assert not tracker.hours


def test_duplicate_and_out_of_order_samples_do_not_rewind_baseline():
    tracker = PeakTracker()
    now = at("2026-10-01T10:00:00+02:00")
    tracker.add(now, 100)
    tracker.add(now, 999)
    tracker.add(now - timedelta(seconds=1), 1)
    tracker.add(now + timedelta(minutes=1), 100.1)
    assert sum(h.kwh for h in tracker.hours.values()) == pytest.approx(0.1)


def test_unchanged_but_fresh_meter_reports_are_real_zero_consumption():
    tracker = PeakTracker()
    now = fill(tracker, at("2026-10-01T10:00:00+02:00"), 1, kw=0)
    data = tracker.snapshot(now, peak_days=1)
    assert data["monthly_peak_kw"] == 0
    assert data["complete_hours"] == 1


def test_short_interval_is_split_at_hour_boundary():
    tracker = PeakTracker()
    tracker.add(at("2026-10-01T10:59:30+02:00"), 100)
    tracker.add(at("2026-10-01T11:00:30+02:00"), 100.1)
    assert len(tracker.hours) == 2
    assert all(h.kwh == pytest.approx(0.05) for h in tracker.hours.values())


def test_three_peaks_must_be_on_distinct_days():
    tracker = PeakTracker()
    day1 = at("2026-10-01T10:00:00+02:00")
    fill(tracker, day1, 2, kw=8)
    assert tracker.snapshot(day1 + timedelta(hours=2))["monthly_peak_kw"] is None
    fill(tracker, day1 + timedelta(days=1), 1, kw=4, total=100)
    now = fill(tracker, day1 + timedelta(days=2), 1, kw=3, total=200)
    data = tracker.snapshot(now)
    assert data["monthly_peak_kw"] == pytest.approx(5)
    assert len({p["date"] for p in data["top_days"]}) == 3


def test_better_hour_replaces_same_day_peak():
    tracker = PeakTracker()
    start = at("2026-10-01T10:00:00+02:00")
    fill(tracker, start, 1, kw=2)
    end = fill(tracker, start + timedelta(hours=1), 1, kw=6, total=2)
    data = tracker.snapshot(end, peak_days=1)
    assert data["monthly_peak_kw"] == pytest.approx(6)
    assert data["days_observed"] == 1


def test_local_month_reset_not_utc_month_reset():
    tracker = PeakTracker()
    start = at("2026-09-30T23:00:00+02:00")
    now = fill(tracker, start, 1, kw=9)
    assert tracker.snapshot(now, peak_days=1)["monthly_peak_kw"] is None
    assert tracker.snapshot(now)["month"] == "2026-10"


def test_autumn_dst_keeps_both_02_hours_but_one_day_peak():
    tracker = PeakTracker()
    start = at("2026-10-25T00:00:00+00:00")
    end = fill(tracker, start, 2, kw=4)
    assert len(tracker.hours) == 2
    labels = [datetime.fromtimestamp(h, UTC).astimezone(engine.OSLO) for h in tracker.hours]
    assert [v.hour for v in labels] == [2, 2]
    assert labels[0].utcoffset() != labels[1].utcoffset()
    data = tracker.snapshot(end, peak_days=1)
    assert data["days_observed"] == 1
    assert data["complete_hours"] == 2
    assert data["monthly_peak_kw"] == pytest.approx(4)


def test_spring_dst_does_not_invent_a_missing_hour():
    tracker = PeakTracker()
    start = at("2026-03-29T00:00:00+00:00")
    end = fill(tracker, start, 2)
    labels = [datetime.fromtimestamp(h, UTC).astimezone(engine.OSLO).hour for h in tracker.hours]
    assert labels == [1, 3]
    assert tracker.snapshot(end, peak_days=1)["complete_hours"] == 2


def test_restart_preserves_peaks_but_does_not_invent_downtime_data():
    tracker = PeakTracker()
    start = at("2026-10-01T10:00:00+02:00")
    end = fill(tracker, start, 1)
    restored = PeakTracker()
    restored.restore(json.loads(json.dumps(tracker.dump())), end)
    restored.add(end + timedelta(minutes=2), 2.2)
    data = restored.snapshot(end + timedelta(minutes=2), peak_days=1)
    assert data["monthly_peak_kw"] == pytest.approx(2)
    assert data["status"] == "incomplete_hour"


def test_stale_energy_or_power_disables_warning():
    tracker = PeakTracker()
    now = at("2026-10-01T10:00:00+02:00")
    tracker.add(now, 0)
    later = now + timedelta(minutes=6)
    data = tracker.snapshot(later, power_kw=12, power_at=later)
    assert data["status"] == "stale"
    assert data["hourly_target_risk"] is None
    data = tracker.snapshot(now, power_kw=12, power_at=now - timedelta(minutes=6))
    assert data["hourly_target_risk"] is None


def test_unavailable_then_returning_source_does_not_bridge_gap():
    tracker = PeakTracker()
    now = at("2026-10-01T10:00:00+02:00")
    tracker.add(now, 100)
    tracker.break_continuity()
    tracker.add(now + timedelta(minutes=1), 101)
    assert not tracker.hours


def test_retention_is_bounded():
    tracker = PeakTracker()
    now = fill(tracker, at("2026-07-01T10:00:00+02:00"), 1)
    tracker.add(now + timedelta(days=63), 1000)
    assert not tracker.hours


def test_corrupt_storage_rejected():
    tracker = PeakTracker()
    with pytest.raises(ValueError):
        tracker.restore(
            {"hours": [{"start": 0, "kwh": -1, "seconds": 3600}]}, at("2026-10-01T00:00:00+02:00")
        )


def test_full_day_coverage_counts_from_local_midnight():
    tracker = PeakTracker()
    start = at("2026-10-01T00:00:00+02:00")
    now = fill(tracker, start, 24)
    assert tracker.snapshot(now)["month_coverage_percent"] == pytest.approx(100)


@pytest.mark.parametrize("gap", [0, 29, 901, float("nan")])
def test_invalid_gap_rejected(gap):
    with pytest.raises(ValueError):
        PeakTracker(gap)


def test_naive_timestamps_rejected():
    with pytest.raises(ValueError):
        PeakTracker().add(datetime(2026, 10, 1), 0)


def test_target_exact_boundary_is_warning_not_false_safety():
    tracker = PeakTracker()
    now = at("2026-10-01T10:00:00+02:00")
    tracker.add(now, 0)
    assert tracker.snapshot(now, power_kw=5, power_at=now)["hourly_target_risk"] is True
