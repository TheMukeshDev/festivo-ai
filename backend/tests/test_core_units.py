"""Core helpers, schema validators, and settings branches exercised in isolation."""

import decimal
from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.exceptions import ResourceNotFoundError
from app.core.ids import parse_uuid
from app.core.money import quantize_money, to_decimal
from app.models.budget import MAX_MONEY, ReserveType
from app.schemas.event import EventCreate
from app.schemas.proposal import (
    ProposalApprovalRequest,
    ProposalGenerationRequest,
    ProposalRejectRequest,
    _normalize_optional_datetime,
)
from app.schemas.task import _normalize_datetime
from app.schemas.vendor import (
    VendorCreate,
    _normalize_currency,
    _normalize_money,
    _validate_email,
    _validate_phone,
    _validate_url,
)
from app.services.ai.schemas import AIPlanResponse, BudgetSuggestion, Recommendation
from app.services.budget_calculator import BudgetCalculationError, calculate_budget_summary

DATABASE_URL = "postgresql://festivo:password@localhost:5432/festivo_test"
NOW = datetime(2030, 5, 15, 8, 0, tzinfo=UTC)


def event_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Ananya and Rohan Wedding",
        "event_type": "wedding",
        "event_date": "2030-06-15",
        "location": "Bengaluru",
        "guest_count": 150,
        "budget_amount": "750000.00",
    }
    payload.update(overrides)
    return payload


class NumericText:
    """Object whose string form is a valid decimal literal."""

    def __str__(self) -> str:
        return "3.25"


class TestMoneyHelpers:
    def test_quantize_rounds_half_up(self) -> None:
        assert quantize_money(Decimal("1.005")) == Decimal("1.01")

    def test_to_decimal_converts_common_input_types(self) -> None:
        assert to_decimal(None) == Decimal("0.00")
        assert to_decimal(Decimal("1.50")) == Decimal("1.50")
        assert to_decimal(7) == Decimal("7")
        assert to_decimal(2.5) == Decimal("2.5")
        assert to_decimal(" 12.50 ") == Decimal("12.50")
        assert to_decimal("   ") == Decimal("0.00")
        assert to_decimal(NumericText()) == Decimal("3.25")

    def test_to_decimal_rejects_booleans_and_unparsable_objects(self) -> None:
        with pytest.raises(ValueError, match="Cannot convert"):
            to_decimal(True)

        with pytest.raises(ValueError, match="Cannot convert"):
            to_decimal(object())


class TestIdentifierParsing:
    def test_a_wrong_uuid_with_the_right_length_is_still_not_found(self) -> None:
        with pytest.raises(ResourceNotFoundError, match=r"Event not found\."):
            parse_uuid("z" * 36, "Event not found.")


class TestBudgetCalculatorLimits:
    def test_a_total_above_the_money_limit_is_rejected(self) -> None:
        with pytest.raises(BudgetCalculationError, match="exceeds the supported"):
            calculate_budget_summary(
                total_limit=MAX_MONEY + Decimal("0.01"),
                reserve_type=ReserveType.PERCENTAGE,
                reserve_value=Decimal("10.00"),
                currency="INR",
                expenses=(),
                guest_count=None,
            )

    def test_a_total_that_cannot_be_quantized_is_rejected(self) -> None:
        with decimal.localcontext() as context:
            context.prec = 1
            with pytest.raises(BudgetCalculationError, match="cannot be represented"):
                calculate_budget_summary(
                    total_limit=Decimal("500000.00"),
                    reserve_type=ReserveType.PERCENTAGE,
                    reserve_value=Decimal("10.00"),
                    currency="INR",
                    expenses=(),
                    guest_count=None,
                )


class TestEventDateParsing:
    def test_a_datetime_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="calendar date"):
            EventCreate(**event_payload(event_date=datetime(2030, 6, 15, 10, 0, tzinfo=UTC)))

    def test_a_date_object_is_accepted(self) -> None:
        event = EventCreate(**event_payload(event_date=date(2030, 6, 15)))
        assert event.event_date == date(2030, 6, 15)

    def test_a_non_string_non_date_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="calendar date"):
            EventCreate(**event_payload(event_date=15062030))

    def test_a_badly_formatted_string_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="calendar date"):
            EventCreate(**event_payload(event_date="15/06/2030"))

    def test_an_impossible_calendar_date_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="valid calendar date"):
            EventCreate(**event_payload(event_date="2030-02-30"))

    def test_a_valid_iso_date_is_accepted(self) -> None:
        event = EventCreate(**event_payload())
        assert event.event_date == date(2030, 6, 15)


class TestEventCurrencyAndTimezone:
    def test_currency_is_normalized_to_uppercase(self) -> None:
        event = EventCreate(**event_payload(currency="inr"))
        assert event.currency == "INR"

    def test_currency_must_be_three_letters(self) -> None:
        with pytest.raises(ValidationError, match="three-letter"):
            EventCreate(**event_payload(currency="1n2"))

    def test_timezone_is_validated_against_iana(self) -> None:
        event = EventCreate(**event_payload(timezone="Asia/Kolkata"))
        assert event.timezone == "Asia/Kolkata"

        with pytest.raises(ValidationError, match="IANA timezone"):
            EventCreate(**event_payload(timezone="Mars/Olympus"))


class TestTaskDueDateNormalization:
    def test_none_stays_none(self) -> None:
        assert _normalize_datetime(None) is None

    def test_an_offset_string_is_converted_to_utc(self) -> None:
        assert _normalize_datetime("2030-06-10T09:00:00+05:30") == datetime(
            2030, 6, 10, 3, 30, tzinfo=UTC
        )
        assert _normalize_datetime("2030-06-10T09:00:00Z") == datetime(
            2030, 6, 10, 9, 0, tzinfo=UTC
        )

    def test_empty_and_unparsable_strings_are_rejected(self) -> None:
        with pytest.raises(ValueError, match="ISO-8601 timestamp"):
            _normalize_datetime("   ")

        with pytest.raises(ValueError, match="ISO-8601 timestamp"):
            _normalize_datetime("not-a-date")

    def test_a_non_datetime_value_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="ISO-8601 timestamp"):
            _normalize_datetime(15)

    def test_a_naive_timestamp_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="timezone offset"):
            _normalize_datetime(datetime(2030, 6, 10, 9, 0))


class TestVendorFieldHelpers:
    def test_currency_is_normalized_and_validated(self) -> None:
        assert _normalize_currency("inr") == "INR"

        with pytest.raises(ValueError, match="three-letter"):
            _normalize_currency("IN")

        with pytest.raises(ValueError, match="three-letter"):
            _normalize_currency("INR1")

    def test_email_is_lowercased_and_validated(self) -> None:
        assert _validate_email("  Priya@Example.COM ") == "priya@example.com"

        with pytest.raises(ValueError, match="Invalid email address"):
            _validate_email("not-an-email")

    def test_website_url_requires_http(self) -> None:
        assert _validate_url("https://example.com") == "https://example.com"

        with pytest.raises(ValueError, match="valid http"):
            _validate_url("ftp://example.com")

        with pytest.raises(ValueError, match="valid http"):
            _validate_url("not-a-url")

    def test_vendor_create_wires_the_url_validator(self) -> None:
        vendor = VendorCreate(
            name="Lotus Banquets",
            category="venue",
            website_url="https://example.com",
        )
        assert vendor.website_url == "https://example.com"

        with pytest.raises(ValidationError, match="valid http"):
            VendorCreate(
                name="Lotus Banquets",
                category="venue",
                website_url="ftp://example.com",
            )

    def test_phone_is_restricted_to_contact_characters(self) -> None:
        assert _validate_phone("+91 90000-00000") == "+91 90000-00000"

        with pytest.raises(ValueError, match="Phone must"):
            _validate_phone("call me!")

    def test_money_is_quantized_and_bounded(self) -> None:
        assert _normalize_money(Decimal("10.005")) == Decimal("10.01")

        with pytest.raises(ValueError, match="finite"):
            _normalize_money(Decimal("NaN"))

        with pytest.raises(ValueError, match="finite"):
            _normalize_money(Decimal("Infinity"))

        with pytest.raises(ValueError, match="cannot be negative"):
            _normalize_money(Decimal("-1.00"))

        with pytest.raises(ValueError, match="exceeds the supported limit"):
            _normalize_money(MAX_MONEY + Decimal("0.01"))


class TestProposalSchemas:
    def test_optional_datetime_normalizer_handles_all_inputs(self) -> None:
        moment = datetime(2030, 6, 10, 9, 0, tzinfo=UTC)
        assert _normalize_optional_datetime(None) is None
        assert _normalize_optional_datetime(moment) == moment

        with pytest.raises(ValueError, match="timezone-aware"):
            _normalize_optional_datetime("2030-06-10T09:00:00Z")

    def test_approval_request_accepts_an_explicit_null_item_list(self) -> None:
        request = ProposalApprovalRequest(item_ids=None)
        assert request.item_ids is None

    def test_rejection_request_deduplicates_selected_items(self) -> None:
        assert ProposalRejectRequest(item_ids=None).item_ids is None

        first, second = uuid4(), uuid4()
        request = ProposalRejectRequest(item_ids=[first, second, first])
        assert request.item_ids == [first, second]

    def test_generation_request_cleans_focus_areas_and_notes(self) -> None:
        request = ProposalGenerationRequest(
            focus_areas=["  Decor  ", "", "   ", "Catering"],
            additional_notes="  Confirm the guest count.  ",
        )
        assert request.focus_areas == ["Decor", "Catering"]
        assert request.additional_notes == "Confirm the guest count."

        blank = ProposalGenerationRequest(additional_notes="   ")
        assert blank.additional_notes is None


class TestAISuggestionSchemas:
    def test_recommendation_assumptions_are_trimmed(self) -> None:
        recommendation = Recommendation(
            category="Decor",
            description="Use seasonal flowers.",
            rationale="Lower cost.",
            assumptions=["  fresh flowers  ", "   "],
        )
        assert recommendation.assumptions == ["fresh flowers"]

    def test_budget_suggestion_normalizes_currency(self) -> None:
        suggestion = BudgetSuggestion(
            category="Decor",
            description="Floral arch",
            rationale="Matches the theme.",
            currency="inr",
        )
        assert suggestion.currency == "INR"

        with pytest.raises(ValidationError, match="3-letter"):
            BudgetSuggestion(
                category="Decor",
                description="Floral arch",
                rationale="Matches the theme.",
                currency="1nr",
            )

    def test_budget_suggestion_amount_is_optional_and_non_negative(self) -> None:
        base = {
            "category": "Decor",
            "description": "Floral arch",
            "rationale": "Matches the theme.",
            "currency": "INR",
        }
        assert BudgetSuggestion(**base, suggested_amount=None).suggested_amount is None

        with pytest.raises(ValidationError, match="non-negative"):
            BudgetSuggestion(**base, suggested_amount=Decimal("-5.00"))

    def test_ai_plan_string_lists_are_cleaned(self) -> None:
        response = AIPlanResponse(
            event_id="evt-1",
            summary="A calm spring wedding.",
            generated_at=NOW,
            model_used="gemini-2.5-flash",
            theme_ideas=["  Spring  ", "", "   ", "Garden"],
        )
        assert response.theme_ideas == ["Spring", "Garden"]

    def test_ai_plan_string_lists_are_capped(self) -> None:
        response = AIPlanResponse(
            event_id="evt-1",
            summary="A calm spring wedding.",
            generated_at=NOW,
            model_used="gemini-2.5-flash",
            risks_and_constraints=[f"risk-{index}" for index in range(80)],
        )
        assert len(response.risks_and_constraints) == 80

    def test_ai_plan_requires_an_event_identifier(self) -> None:
        with pytest.raises(ValidationError, match="event_id required"):
            AIPlanResponse(
                event_id="",
                summary="A calm spring wedding.",
                generated_at=NOW,
                model_used="gemini-2.5-flash",
            )


class TestSettingsValidation:
    def test_blank_application_name_is_rejected(
        self,
        make_settings: Callable[..., Settings],
    ) -> None:
        with pytest.raises(ValidationError, match="APP_NAME must not be blank"):
            make_settings(app_name="   ")

    def test_invalid_api_prefix_is_rejected(
        self,
        make_settings: Callable[..., Settings],
    ) -> None:
        with pytest.raises(ValidationError, match="API_V1_PREFIX"):
            make_settings(api_v1_prefix="api/v1")

    def test_malformed_database_url_raises_a_validation_error(
        self,
        make_settings: Callable[..., Settings],
    ) -> None:
        with pytest.raises(ValidationError, match="SUPABASE_DB_URL"):
            make_settings(supabase_db_url="postgresql://[bad")

    def test_supabase_project_url_rejects_paths(
        self, make_settings: Callable[..., Settings]
    ) -> None:
        with pytest.raises(ValidationError, match="SUPABASE_URL"):
            make_settings(supabase_url="https://project.supabase.co/auth/v1")

    def test_blank_authentication_urls_treated_as_unset(
        self, make_settings: Callable[..., Settings]
    ) -> None:
        settings = make_settings(supabase_jwks_url="   ")
        assert settings.supabase_jwks_url is None

    def test_invalid_authentication_url_is_rejected(
        self, make_settings: Callable[..., Settings]
    ) -> None:
        with pytest.raises(ValidationError, match="authentication URLs"):
            make_settings(supabase_jwks_url="not-a-url")

    def test_malformed_json_origin_list_is_rejected(
        self, make_settings: Callable[..., Settings]
    ) -> None:
        with pytest.raises(ValidationError, match="comma-separated list or a JSON array"):
            make_settings(frontend_origins='["https://app.example.com"')

    def test_origins_must_be_a_list(self, make_settings: Callable[..., Settings]) -> None:
        with pytest.raises(ValidationError, match="one or more origins"):
            make_settings(frontend_origins=42)

    def test_an_empty_origin_list_is_rejected(self, make_settings: Callable[..., Settings]) -> None:
        with pytest.raises(ValidationError, match="At least one frontend origin"):
            make_settings(frontend_origins="[]")

    def test_origins_must_be_strings(self) -> None:
        with pytest.raises(ValueError, match="must be a string"):
            Settings.validate_frontend_origins([123])

    def test_origins_with_a_bad_port_are_rejected(
        self, make_settings: Callable[..., Settings]
    ) -> None:
        with pytest.raises(ValidationError, match="Invalid port in frontend origin"):
            make_settings(frontend_origins=["https://app.example.com:notaport"])

    def test_origins_with_a_non_http_scheme_are_rejected(
        self, make_settings: Callable[..., Settings]
    ) -> None:
        with pytest.raises(ValidationError, match="http"):
            make_settings(frontend_origins=["ftp://app.example.com"])

    def test_a_non_string_model_name_is_rejected(
        self, make_settings: Callable[..., Settings]
    ) -> None:
        with pytest.raises(ValidationError, match="LLM_MODEL must be a string"):
            make_settings(llm_model=123)

    def test_production_requires_a_firebase_project(
        self, make_settings: Callable[..., Settings]
    ) -> None:
        with pytest.raises(ValidationError, match="FIREBASE_PROJECT_ID"):
            make_settings(
                app_env="production",
                debug=False,
                storage_backend="postgres",
                supabase_db_url=DATABASE_URL,
                firebase_project_id=None,
            )


class TestSettingsProperties:
    def test_resolved_auth_urls_are_derived_from_the_project_url(self) -> None:
        explicit = make_settings_explicit(
            supabase_jwks_url="https://keys.example.com/jwks",
            supabase_jwt_issuer="https://issuer.example.com",
        )
        assert explicit.resolved_jwks_url == "https://keys.example.com/jwks"
        assert explicit.resolved_jwt_issuer == "https://issuer.example.com"

        derived = make_settings_explicit(supabase_url="https://project.supabase.co")
        assert (
            derived.resolved_jwks_url == "https://project.supabase.co/auth/v1/.well-known/jwks.json"
        )
        assert derived.resolved_jwt_issuer == "https://project.supabase.co/auth/v1"

        bare = make_settings_explicit()
        assert bare.resolved_jwks_url is None
        assert bare.resolved_jwt_issuer is None

    def test_auth_configured_aliases_the_firebase_flag(self) -> None:
        configured = make_settings_explicit(firebase_project_id="festivo-test")
        assert configured.auth_configured is True

        unconfigured = make_settings_explicit(firebase_project_id=None)
        assert unconfigured.auth_configured is False

    def test_llm_state_reports_an_incomplete_configuration(self) -> None:
        settings = Settings.model_construct(
            llm_enabled=True,
            gemini_api_key=None,
            llm_model=None,
        )
        assert settings.llm_configuration_state == "incomplete"


def make_settings_explicit(**overrides: object) -> Settings:
    """Build settings directly so property branches can be inspected."""
    values: dict[str, object] = {"_env_file": None, "app_env": "test"}
    values.update(overrides)
    return Settings(**values)
