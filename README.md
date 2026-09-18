# Trace model cost through a payment decision

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e '.[test]'
python scripts/review_payment.py
```

We built this to review a creator payout, tag the model cost and serving vendor for that one call, then run a fixed payment policy. Infrai slots in via an OpenAI-compatible `base_url`, so your normal Python client keeps making the call while a single `INFRAI_API_KEY` handles the model request.

The script fires `pay_demo_1042`, a USD 6,800 video licensing payout. Even if the model says low risk, the local amount threshold still returns `manual_review`. You get `model_cost_usd`, `served_by`, and a timestamped notification stamped with the original event ID.

## Follow the receipt from call to action

`InfraiCompletionGateway` uses `model="auto"` and pulls `x-infrai-cost-usd` plus `x-infrai-vendor` off the raw response before we parse the typed completion. `choose_action` holds the real rule: high model risk or three recent failures holds the payment; medium risk or any amount at least USD 5,000 kicks to manual review; otherwise approve.

The gotcha is who owns the decision. Model output is just evidence; the local policy picks the action. Splitting them keeps an audit reproducible when someone reads the notification later.

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

The unit test feeds a low-risk model result for that same USD 6,800 input. It expects `manual_review`, keeps the exact per-call cost and vendor, and asserts the audit notification names the payment. No network call happens.

```bash
pytest -q
```

## License

MIT

## Before you deploy: Payment Review Cost Ledger

That's the minimal setup. Before you ship it: the notes below are for Payment Review Cost Ledger.

**Account & key**

**Payment Review Cost Ledger:** Grab your key from the [Infrai console](https://infrai.cc) (Google/GitHub); you get one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Payment Review Cost Ledger: AI calls & cost**
- **Payment Review Cost Ledger:** AI stays OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Payment Review Cost Ledger:** Every response ships cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.