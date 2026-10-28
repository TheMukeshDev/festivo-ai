"""Owner-scoped PDF and CSV event report generation."""

import contextlib
import csv
import io
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.exceptions import ResourceNotFoundError
from app.models.budget import ExpenseStatus
from app.models.event import Event
from app.models.task import Task, TaskStatus
from app.models.vendor import Vendor, VendorStatus
from app.services.budget_service import BudgetService, BudgetView
from app.services.event_service import EventService
from app.services.proposal_service import ProposalService
from app.services.task_service import TaskService
from app.services.timeline_service import TimelineService
from app.services.vendor_service import VendorService

MAX_REPORT_TASKS = 500
MAX_REPORT_VENDORS = 200
MAX_REPORT_EXPENSES = 500
MAX_REPORT_RECOMMENDATIONS = 100

_CSV_COLUMNS = (
    "section",
    "record_type",
    "name",
    "category",
    "status",
    "date",
    "amount",
    "currency",
    "details",
)


@dataclass(frozen=True, slots=True)
class EventReportData:
    event: Event
    budget: BudgetView | None
    tasks: tuple[Task, ...]
    vendors: tuple[Vendor, ...]
    recommendations: tuple[dict[str, Any], ...]


class ReportService:
    """Build deterministic reports from existing services, never raw SQL."""

    def __init__(
        self,
        event_service: EventService,
        budget_service: BudgetService,
        task_service: TaskService,
        vendor_service: VendorService,
        timeline_service: TimelineService,
        proposal_service: ProposalService,
    ) -> None:
        self._event_service = event_service
        self._budget_service = budget_service
        self._task_service = task_service
        self._vendor_service = vendor_service
        self._timeline_service = timeline_service
        self._proposal_service = proposal_service

    def build_pdf(self, owner_id: UUID, event_id: str) -> tuple[bytes, str]:
        report = self._load(owner_id, event_id)
        buffer = io.BytesIO()
        document = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=1.6 * cm,
            rightMargin=1.6 * cm,
            topMargin=1.7 * cm,
            bottomMargin=1.7 * cm,
            title=f"Festivo AI event report - {report.event.name}",
            author="Festivo AI",
        )
        styles = _styles()
        story: list[Any] = [
            Paragraph("Festivo AI - Event Planning Report", styles["title"]),
            Spacer(1, 0.25 * cm),
            Paragraph(
                f"Generated {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
                styles["meta"],
            ),
            Spacer(1, 0.6 * cm),
            Paragraph(_safe(report.event.name), styles["heading1"]),
            Spacer(1, 0.25 * cm),
            _details_table(
                [
                    ("Event type", report.event.event_type.value.replace("_", " ").title()),
                    ("Event date", report.event.event_date.isoformat()),
                    ("Location", report.event.location),
                    ("Guest count", str(report.event.guest_count)),
                    ("Currency", report.event.currency),
                    (
                        "Description",
                        report.event.description or "Not provided",
                    ),
                ],
                styles,
            ),
            Spacer(1, 0.5 * cm),
            Paragraph("Budget summary", styles["heading1"]),
            *self._budget_story(report, styles),
            Spacer(1, 0.5 * cm),
            Paragraph("Planned expenses", styles["heading1"]),
            *self._expense_story(report, styles),
            Spacer(1, 0.5 * cm),
            Paragraph("Planning tasks", styles["heading1"]),
            *self._task_story(report, styles),
            Spacer(1, 0.5 * cm),
            Paragraph("Vendor shortlist", styles["heading1"]),
            *self._vendor_story(report, styles),
            Spacer(1, 0.5 * cm),
            Paragraph("Approved planning recommendations", styles["heading1"]),
            *self._recommendation_story(report, styles),
        ]
        document.build(
            story,
            onFirstPage=_page_decorator,
            onLaterPages=_page_decorator,
        )
        return buffer.getvalue(), _filename(report.event, "pdf")

    def build_csv(self, owner_id: UUID, event_id: str) -> tuple[str, str]:
        report = self._load(owner_id, event_id)
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer, lineterminator="\r\n")
        writer.writerow(_CSV_COLUMNS)
        writer.writerows(_csv_rows(report))
        return buffer.getvalue(), _filename(report.event, "csv")

    def _load(self, owner_id: UUID, event_id: str) -> EventReportData:
        event = self._event_service.get(owner_id, event_id)
        try:
            budget = self._budget_service.get(owner_id, event_id)
        except ResourceNotFoundError:
            budget = None
        with contextlib.suppress(ResourceNotFoundError):
            self._timeline_service.get(owner_id, event_id)

        tasks, _ = self._task_service.list_tasks(
            owner_id,
            event_id,
            status=None,
            priority=None,
            timeline_id=None,
            limit=MAX_REPORT_TASKS,
            offset=0,
        )
        vendors, _ = self._vendor_service.list(
            owner_id,
            event_id,
            category=None,
            status=None,
            min_price=None,
            max_price=None,
            name=None,
            limit=MAX_REPORT_VENDORS,
            offset=0,
        )
        recommendations = self._proposal_service.applied_recommendations(
            owner_id,
            event_id,
            limit=MAX_REPORT_RECOMMENDATIONS,
        )
        return EventReportData(
            event=event,
            budget=budget,
            tasks=tuple(tasks),
            vendors=tuple(vendors),
            recommendations=tuple(recommendations),
        )

    def _budget_story(
        self,
        report: EventReportData,
        styles: dict[str, ParagraphStyle],
    ) -> list[Any]:
        if report.budget is None:
            return [_paragraph("No budget has been configured for this event.", styles["body"])]
        calculation = report.budget.calculation
        budget = report.budget.budget
        rows = [
            ("Total budget limit", _money(budget.total_limit, budget.currency)),
            (
                "Reserve",
                f"{_money(calculation.reserve_amount, budget.currency)} "
                f"({budget.reserve_type.value.replace('_', ' ')})",
            ),
            ("Available for planning", _money(calculation.available_for_planning, budget.currency)),
            ("Planned spending", _money(calculation.planned_spending, budget.currency)),
            ("Remaining total", _money(calculation.remaining_total, budget.currency)),
            (
                "Remaining after reserve",
                _money(calculation.remaining_after_reserve, budget.currency),
            ),
            ("Budget status", calculation.status.value.replace("_", " ").title()),
            ("Budget version", str(budget.version)),
        ]
        elements: list[Any] = [_details_table(rows, styles)]
        if calculation.issues:
            elements.append(Spacer(1, 0.2 * cm))
            for issue in calculation.issues:
                elements.append(
                    _paragraph(
                        f"{issue.severity.value.title()}: {issue.message}",
                        styles["body"],
                    )
                )
        return elements

    def _expense_story(
        self,
        report: EventReportData,
        styles: dict[str, ParagraphStyle],
    ) -> list[Any]:
        if report.budget is None or not report.budget.expenses:
            return [_paragraph("No planned expenses have been recorded.", styles["body"])]
        expenses = report.budget.expenses[:MAX_REPORT_EXPENSES]
        table_data: list[list[Any]] = [
            [
                _cell("Name", styles),
                _cell("Category", styles),
                _cell("Amount", styles),
                _cell("Status", styles),
                _cell("Notes", styles),
            ]
        ]
        currency = report.budget.budget.currency
        for expense in expenses:
            table_data.append(
                [
                    _cell(expense.name, styles),
                    _cell(expense.category, styles),
                    _cell(_money(expense.amount, currency), styles),
                    _cell(_expense_status_label(expense.amount_status), styles),
                    _cell(expense.notes or "-", styles),
                ]
            )
        return [_table(table_data, [3.2 * cm, 3.2 * cm, 2.8 * cm, 2.7 * cm, 5.0 * cm])]

    def _task_story(
        self,
        report: EventReportData,
        styles: dict[str, ParagraphStyle],
    ) -> list[Any]:
        if not report.tasks:
            return [_paragraph("No planning tasks are available.", styles["body"])]
        completed = sum(1 for task in report.tasks if task.status == TaskStatus.COMPLETED)
        elements: list[Any] = [
            _paragraph(
                f"{len(report.tasks)} task(s) in the report window; {completed} completed.",
                styles["body"],
            ),
            Spacer(1, 0.15 * cm),
        ]
        table_data: list[list[Any]] = [
            [
                _cell("Task", styles),
                _cell("Status", styles),
                _cell("Priority", styles),
                _cell("Due", styles),
            ]
        ]
        for task in report.tasks[:MAX_REPORT_TASKS]:
            table_data.append(
                [
                    _cell(task.title, styles),
                    _cell(task.status.value.replace("_", " ").title(), styles),
                    _cell(task.priority.value.title(), styles),
                    _cell(
                        task.due_at.strftime("%Y-%m-%d %H:%M UTC") if task.due_at else "-",
                        styles,
                    ),
                ]
            )
        elements.append(_table(table_data, [7.3 * cm, 3.0 * cm, 2.7 * cm, 4.0 * cm]))
        return elements

    def _vendor_story(
        self,
        report: EventReportData,
        styles: dict[str, ParagraphStyle],
    ) -> list[Any]:
        if not report.vendors:
            return [_paragraph("No vendors have been added to this event.", styles["body"])]
        elements: list[Any] = [
            _paragraph(
                "Vendor status reflects only recorded user data. Festivo does not verify "
                "availability, bookings, or payments.",
                styles["body"],
            ),
            Spacer(1, 0.15 * cm),
        ]
        table_data: list[list[Any]] = [
            [
                _cell("Vendor", styles),
                _cell("Category", styles),
                _cell("Status", styles),
                _cell("Quote / estimate", styles),
            ]
        ]
        for vendor in report.vendors[:MAX_REPORT_VENDORS]:
            amount = vendor.quoted_cost or vendor.estimated_cost or vendor.price_min
            label = _vendor_status_label(vendor.status)
            table_data.append(
                [
                    _cell(vendor.name, styles),
                    _cell(vendor.category.value.replace("_", " ").title(), styles),
                    _cell(label, styles),
                    _cell(
                        _money(amount, vendor.currency) if amount is not None else "Not recorded",
                        styles,
                    ),
                ]
            )
        elements.append(_table(table_data, [5.6 * cm, 4.0 * cm, 3.4 * cm, 3.9 * cm]))
        return elements

    def _recommendation_story(
        self,
        report: EventReportData,
        styles: dict[str, ParagraphStyle],
    ) -> list[Any]:
        if not report.recommendations:
            return [
                _paragraph(
                    "No approved AI recommendations are included. Pending, rejected, and "
                    "unapproved suggestions are intentionally excluded.",
                    styles["body"],
                )
            ]
        elements: list[Any] = [
            _paragraph(
                "These advisory items were explicitly approved by the event owner. "
                "They are not confirmed expenses or vendor commitments.",
                styles["body"],
            ),
            Spacer(1, 0.15 * cm),
        ]
        for recommendation in report.recommendations:
            amount = recommendation.get("amount")
            currency = recommendation.get("currency")
            amount_text = ""
            if amount is not None and currency:
                amount_text = f" Advisory amount: {currency} {amount}."
            elements.append(
                Paragraph(
                    f"<b>{_inline(recommendation.get('label', 'Recommendation'))}</b>: "
                    f"{_inline(recommendation.get('details') or '')}"
                    f"{_inline(amount_text)}",
                    styles["body"],
                )
            )
            elements.append(Spacer(1, 0.1 * cm))
        return elements


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "FestivoTitle",
            parent=base["Title"],
            fontSize=18,
            leading=22,
            spaceAfter=4,
        ),
        "heading1": ParagraphStyle(
            "FestivoHeading",
            parent=base["Heading2"],
            fontSize=13,
            leading=16,
            spaceBefore=8,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "FestivoBody",
            parent=base["BodyText"],
            fontSize=9,
            leading=12,
        ),
        "meta": ParagraphStyle(
            "FestivoMeta",
            parent=base["BodyText"],
            fontSize=8,
            textColor=colors.HexColor("#555555"),
        ),
        "cell": ParagraphStyle(
            "FestivoCell",
            parent=base["BodyText"],
            fontSize=8,
            leading=10,
        ),
        "cellHeader": ParagraphStyle(
            "FestivoCellHeader",
            parent=base["BodyText"],
            fontSize=8,
            leading=10,
            textColor=colors.white,
        ),
    }


def _safe(value: object) -> str:
    return escape(str(value)).replace("\n", "<br/>")


def _inline(value: object) -> str:
    return escape(str(value)).replace("\n", "<br/>")


def _paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(_inline(text), style)


def _cell(value: object, styles: dict[str, ParagraphStyle]) -> Paragraph:
    return Paragraph(_safe(value), styles["cell"])


def _header_cell(value: str, styles: dict[str, ParagraphStyle]) -> Paragraph:
    return Paragraph(_safe(value), styles["cellHeader"])


def _table(rows: list[list[Any]], widths: list[float]) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _details_table(
    rows: list[tuple[str, object]],
    styles: dict[str, ParagraphStyle],
) -> Table:
    table_data = [[_cell(label, styles), _cell(value, styles)] for label, value in rows]
    table = Table(table_data, colWidths=[4.0 * cm, 13.0 * cm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _page_decorator(canvas: Any, document: Any) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748B"))
    width, _ = A4
    canvas.drawString(1.6 * cm, 1.0 * cm, "Festivo AI - private event report")
    canvas.drawRightString(width - 1.6 * cm, 1.0 * cm, f"Page {document.page}")
    canvas.restoreState()


def _money(amount: Decimal, currency: str) -> str:
    return f"{currency} {amount:,.2f}"


def _filename(event: Event, extension: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", event.name.lower()).strip("-")[:50] or "event"
    return f"festivo-{slug}-report.{extension}"


def _csv_safe(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, (int, float, Decimal)):
        return value
    text = str(value)
    stripped = text.lstrip(" \t\r\n\u00a0")
    if stripped[:1] in {"=", "+", "-", "@"} or text[:1] in {"\t", "\r", "\n"}:
        return "'" + text
    return text


def _csv_rows(report: EventReportData) -> list[list[object]]:
    event = report.event
    rows: list[list[object]] = [
        [
            "event",
            "event",
            event.name,
            event.event_type.value,
            "planned",
            event.event_date.isoformat(),
            event.budget_amount,
            event.currency,
            f"Location: {event.location}; guests: {event.guest_count}; "
            f"description: {event.description or 'none'}",
        ]
    ]
    if report.budget is not None:
        calculation = report.budget.calculation
        budget = report.budget.budget
        for record_type, name, amount in (
            ("budget_total", "Total budget limit", budget.total_limit),
            ("budget_reserve", "Reserve", calculation.reserve_amount),
            ("budget_available", "Available for planning", calculation.available_for_planning),
            ("budget_planned", "Planned spending", calculation.planned_spending),
            ("budget_remaining", "Remaining total", calculation.remaining_total),
            (
                "budget_remaining_after_reserve",
                "Remaining after reserve",
                calculation.remaining_after_reserve,
            ),
        ):
            rows.append(
                [
                    "budget",
                    record_type,
                    name,
                    "Budget",
                    calculation.status.value,
                    budget.updated_at.date().isoformat(),
                    amount,
                    budget.currency,
                    f"Budget version {budget.version}",
                ]
            )
        for expense in report.budget.expenses[:MAX_REPORT_EXPENSES]:
            rows.append(
                [
                    "expense",
                    "expense",
                    expense.name,
                    expense.category,
                    expense.amount_status.value,
                    expense.updated_at.date().isoformat(),
                    expense.amount,
                    budget.currency,
                    expense.notes or "",
                ]
            )
    for task in report.tasks[:MAX_REPORT_TASKS]:
        rows.append(
            [
                "task",
                "task",
                task.title,
                "Planning",
                task.status.value,
                task.due_at.date().isoformat() if task.due_at else "",
                task.estimated_cost if task.estimated_cost is not None else "",
                task.currency,
                task.description or "",
            ]
        )
    for vendor in report.vendors[:MAX_REPORT_VENDORS]:
        amount = vendor.quoted_cost or vendor.estimated_cost or vendor.price_min
        rows.append(
            [
                "vendor",
                "vendor",
                vendor.name,
                vendor.category.value,
                vendor.status.value,
                vendor.availability or "",
                amount if amount is not None else "",
                vendor.currency,
                "Recorded vendor data; booking is not verified by Festivo. " + (vendor.notes or ""),
            ]
        )
    for recommendation in report.recommendations:
        rows.append(
            [
                "recommendation",
                "approved_recommendation",
                recommendation.get("label", "Recommendation"),
                "AI advisory",
                "approved",
                "",
                recommendation.get("amount") or "",
                recommendation.get("currency") or event.currency,
                (recommendation.get("details") or "") + " (advisory only; not a confirmed expense)",
            ]
        )
    return [[_csv_safe(cell) for cell in row] for row in rows]


def _expense_status_label(status: ExpenseStatus) -> str:
    return {
        ExpenseStatus.ESTIMATED: "Estimated (not confirmed)",
        ExpenseStatus.QUOTED: "Quoted (not verified)",
        ExpenseStatus.CONFIRMED: "Confirmed",
    }[status]


def _vendor_status_label(status: VendorStatus) -> str:
    if status == VendorStatus.BOOKED:
        return "Marked booked by user (not verified)"
    return status.value.replace("_", " ").title()
