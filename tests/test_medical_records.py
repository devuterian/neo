from datetime import date

import pytest

from neo.domain.medical import add_record, cycle_status, empty_store, record_event, remove_record, with_status
from neo.errors import NotFoundError, ValidationError


def test_multiple_providers_keep_independent_cycles():
    store, dental_id = add_record(empty_store(), provider="Sample Dental", title="Check-up", last_date="2026-07-01", cycle_days=180)
    store, clinic_id = add_record(store, provider="Sample Clinic", title="Follow-up", last_date="2026-07-10", cycle_days=30)
    rendered = with_status(store, today=date(2026, 7, 20))
    by_id = {item["medical_id"]: item for item in rendered["records"]}
    assert by_id[dental_id]["status"]["next_due"] == "2026-12-28"
    assert by_id[clinic_id]["status"]["next_due"] == "2026-08-09"


def test_record_event_resets_only_selected_cycle():
    store, first = add_record(empty_store(), provider="A", title="A", last_date="2026-07-01", cycle_days=14)
    store, second = add_record(store, provider="B", title="B", last_date="2026-07-02", cycle_days=60)
    updated = record_event(store, first, at="2026-07-20")
    assert updated["records"][0]["last_date"] == "2026-07-20"
    assert updated["records"][1]["medical_id"] == second
    assert updated["records"][1]["last_date"] == "2026-07-02"


def test_one_off_record_has_no_cycle_status_and_can_be_removed():
    store, record_id = add_record(empty_store(), provider="Hospital", title="Consultation", last_date="2026-07-20")
    assert "status" not in with_status(store)["records"][0]
    assert remove_record(store, record_id)["records"] == []
    with pytest.raises(NotFoundError):
        remove_record(store, record_id + "-missing")


def test_cycle_rejects_zero_days():
    with pytest.raises(ValidationError):
        cycle_status("2026-07-20", 0)
