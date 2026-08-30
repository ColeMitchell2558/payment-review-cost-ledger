"""HTTP entry point for payment review decisions."""

from fastapi import FastAPI

from .payment_review import PaymentEvent, ReviewDecision, review_payment

service = FastAPI(title="Payment review cost ledger")


@service.post("/payment-reviews", response_model=ReviewDecision)
def create_payment_review(event: PaymentEvent) -> ReviewDecision:
    return review_payment(event)
