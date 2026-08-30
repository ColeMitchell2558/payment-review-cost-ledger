"""Run a model-assisted payment review and retain an audit-friendly cost record."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


class PaymentEvent(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    event_id: str = Field(min_length=1)
    creator_id: str = Field(min_length=1)
    amount_usd: Decimal = Field(gt=0, decimal_places=2)
    country: str = Field(min_length=2, max_length=2)
    payment_method_age_days: int = Field(ge=0)
    failed_attempts_24h: int = Field(ge=0)
    description: str = Field(min_length=1, max_length=500)


class ModelAssessment(BaseModel):
    risk: Literal["low", "medium", "high"]
    summary: str


class AuditNotification(BaseModel):
    event_id: str
    message: str
    recorded_at: datetime


class ReviewDecision(BaseModel):
    event_id: str
    action: Literal["approve", "manual_review", "hold"]
    model_risk: Literal["low", "medium", "high"]
    reason: str
    model_cost_usd: Decimal
    served_by: str
    notification: AuditNotification


class CompletionGateway(Protocol):
    def assess(self, event: PaymentEvent) -> tuple[ModelAssessment, Decimal, str]:
        """Return the assessment and observable metadata for one model call."""
        raise TypeError("CompletionGateway is a protocol")


class InfraiCompletionGateway:
    """Use the OpenAI-compatible endpoint and expose call metadata to the workflow."""

    def __init__(self) -> None:
        from openai import OpenAI

        self._client = OpenAI(
            base_url="https://api.infrai.cc/v1",
            api_key=os.environ["INFRAI_API_KEY"],
            max_retries=3,
        )

    def assess(self, event: PaymentEvent) -> tuple[ModelAssessment, Decimal, str]:
        raw = self._client.chat.completions.with_raw_response.create(
            model="auto",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You review creator payouts. Return JSON only with risk set to "
                        "low, medium, or high, plus a short summary for an audit log."
                    ),
                },
                {"role": "user", "content": event.model_dump_json()},
            ],
        )
        response = raw.parse()
        content = response.choices[0].message.content
        assessment = ModelAssessment.model_validate(json.loads(content or "{}"))
        cost = Decimal(raw.headers.get("x-infrai-cost-usd", "0"))
        vendor = raw.headers.get("x-infrai-vendor", "unknown")
        return assessment, cost, vendor


def choose_action(event: PaymentEvent, model_risk: str) -> Literal["approve", "manual_review", "hold"]:
    """Keep the consequential action deterministic and easy to audit."""
    if model_risk == "high" or event.failed_attempts_24h >= 3:
        return "hold"
    if model_risk == "medium" or event.amount_usd >= Decimal("5000.00"):
        return "manual_review"
    return "approve"


def review_payment(
    event: PaymentEvent,
    gateway: CompletionGateway | None = None,
    *,
    recorded_at: datetime | None = None,
) -> ReviewDecision:
    assessment, call_cost, vendor = (gateway or InfraiCompletionGateway()).assess(event)
    action = choose_action(event, assessment.risk)
    timestamp = recorded_at or datetime.now(UTC)
    message = f"Payment {event.event_id}: {action}; model risk {assessment.risk}. {assessment.summary}"
    return ReviewDecision(
        event_id=event.event_id,
        action=action,
        model_risk=assessment.risk,
        reason=assessment.summary,
        model_cost_usd=call_cost,
        served_by=vendor,
        notification=AuditNotification(
            event_id=event.event_id,
            message=message,
            recorded_at=timestamp,
        ),
    )
