"""Direct coverage for report formatting helpers and small core utilities."""

from decimal import Decimal

import pytest

from app.api.v1 import tasks
from app.api.v1.timelines import router as timelines_router
from app.core.exceptions import ResourceNotFoundError
from app.core.ids import parse_uuid
from app.models.budget import ExpenseStatus
from app.models.vendor import VendorStatus
from app.services.report_service import (
    _csv_safe,
    _expense_status_label,
    _header_cell,
    _money,
    _styles,
    _vendor_status_label,
)


def test_tasks_router_is_reexported() -> None:
    assert tasks.router is timelines_router


def test_parse_uuid_rejects_non_canonical_hyphen_positions() -> None:
    with pytest.raises(ResourceNotFoundError):
        parse_uuid("1234-5678-1234-5678-1234567812345678", "task")


def test_csv_safe_neutralises_spreadsheet_formulas() -> None:
    assert _csv_safe(None) == ""
    assert _csv_safe(10) == 10
    assert _csv_safe(Decimal("1.5")) == Decimal("1.5")
    assert _csv_safe("=SUM(A1:A2)") == "'=SUM(A1:A2)"
    assert _csv_safe("+plus") == "'+plus"
    assert _csv_safe("-minus") == "'-minus"
    assert _csv_safe("@handle") == "'@handle"
    assert _csv_safe("\tindented") == "'\tindented"
    assert _csv_safe("plain") == "plain"


def test_report_formatting_helpers_cover_every_status() -> None:
    styles = _styles()

    assert _header_cell("Planned spend", styles).text == "Planned spend"
    assert _money(Decimal("1234.5"), "INR") == "INR 1,234.50"
    assert _expense_status_label(ExpenseStatus.ESTIMATED) == "Estimated (not confirmed)"
    assert _expense_status_label(ExpenseStatus.QUOTED) == "Quoted (not verified)"
    assert _expense_status_label(ExpenseStatus.CONFIRMED) == "Confirmed"
    assert _vendor_status_label(VendorStatus.BOOKED) == "Marked booked by user (not verified)"
    assert _vendor_status_label(VendorStatus.DISCOVERED) == "Discovered"
