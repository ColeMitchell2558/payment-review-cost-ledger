"""Run one creator payout through the review workflow."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from payment_cost_ledger import PaymentEvent, review_payment


event = PaymentEvent(
    event_id="pay_demo_1042",
    creator_id="creator_77",
    amount_usd="6800.00",
    country="US",
    payment_method_age_days=240,
    failed_attempts_24h=0,
    description="August video licensing payout",
)

print(review_payment(event).model_dump_json(indent=2))
