from datetime import UTC, datetime
from decimal import Decimal

from payment_cost_ledger.payment_review import ModelAssessment, PaymentEvent, review_payment


class LowRiskGateway:
    def assess(self, event: PaymentEvent) -> tuple[ModelAssessment, Decimal, str]:
        return ModelAssessment(risk="low", summary="Established payout pattern."), Decimal("0.0014"), "demo-vendor"


def test_large_low_risk_payment_still_requires_manual_review() -> None:
    event = PaymentEvent(
        event_id="pay_1042",
        creator_id="creator_77",
        amount_usd="6800.00",
        country="US",
        payment_method_age_days=240,
        failed_attempts_24h=0,
        description="Video licensing payout",
    )
    recorded_at = datetime(2026, 8, 27, 10, 0, tzinfo=UTC)

    decision = review_payment(event, LowRiskGateway(), recorded_at=recorded_at)

    assert decision.action == "manual_review"
    assert decision.model_cost_usd == Decimal("0.0014")
    assert decision.served_by == "demo-vendor"
    assert decision.notification.event_id == event.event_id
    assert decision.notification.recorded_at == recorded_at
    assert "manual_review" in decision.notification.message
