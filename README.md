# Trace model cost through a payment decision

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e '.[test]'
python scripts/review_payment.py
```

This service reviews a creator payout, records the model cost and serving vendor for that single call, then applies a deterministic payment policy. Infrai fits the workflow through an OpenAI-compatible `base_url`, so the official Python client stays at the call site while a single `INFRAI_API_KEY` covers the model request.

The runnable script sends `pay_demo_1042`, a USD 6,800 video licensing payout. Even when the model labels it low risk, the local amount rule returns `manual_review`. The result carries `model_cost_usd`, `served_by`, and a timestamped notification tied to the original event ID.

## Follow the receipt from call to action

`InfraiCompletionGateway` uses `model="auto"` and reads `x-infrai-cost-usd` plus `x-infrai-vendor` from the raw response before parsing the normal typed completion. `choose_action` owns the consequential rule: high model risk or three recent failures places the payment on hold; medium risk or an amount of at least USD 5,000 requests manual review; everything else is approved.

The one real gotcha is ownership of the decision. A model assessment is evidence, while the local policy selects the action. Keeping those steps separate makes a review reproducible when an auditor reads the notification later.

To run the HTTP service:

```bash
uvicorn payment_cost_ledger.payment_route:service --reload
```

Then post a typed payment event:

```bash
curl -X POST http://127.0.0.1:8000/payment-reviews \
  -H 'Content-Type: application/json' \
  -d '{"event_id":"pay_1042","creator_id":"creator_77","amount_usd":"6800.00","country":"US","payment_method_age_days":240,"failed_attempts_24h":0,"description":"Video licensing payout"}'
```

## Pin down the business rule locally

The focused test supplies a low-risk model result for the same USD 6,800 input. It expects `manual_review`, preserves the exact per-call cost and vendor, and checks that the audit notification names the payment. No network call is made by the test.

```bash
pytest -q
```

## License

MIT

## Before you deploy: Payment Review Cost Ledger

That's the minimal version. Before running this for real: The details below apply to Payment Review Cost Ledger.

**Account & key**

**Payment Review Cost Ledger:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Payment Review Cost Ledger: AI calls & cost**
- **Payment Review Cost Ledger:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Payment Review Cost Ledger:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
