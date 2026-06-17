# NN Fund Management (Odoo 17)

Allocate, hold, requisition, bill and transfer funds with a **GM → MD** approval
chain, built on an append-only fund-movement ledger. Every balance is a computed
sum over the immutable `nn.fund.movement` ledger — no balance is ever edited by
hand, so the same money can never be allocated, transferred or spent twice.

## Run it

```bash
docker compose up -d
```

Then open http://localhost:8069 and select database **`nn_test`**.

To (re)install or update the module after code changes:

```bash
docker compose run --rm odoo odoo -d nn_test -u nn_fund_management --stop-after-init
```

## Login credentials

Log in at http://localhost:8069 (database **`nn_test`**) with email + password.
All demo accounts share the password **`admin123`**.

| Email | Password | Role |
|---|---|---|
| `admin@nn.test` | `admin123` | Administrator — full backend, start here |
| `finance_demo@nn.test` | `admin123` | Finance User — confirms incoming funds, sees all requests |
| `fund_demo@nn.test` | `admin123` | Fund User — raises requests, sees only own |
| `gm_demo@nn.test` | `admin123` | GM Approver — first-level approval |
| `md_demo@nn.test` | `admin123` | MD Approver — final approval (posts the money effect) |

Start as `admin@nn.test`, open the **NN Fund Management** app from the apps menu.

To walk the approval chain end-to-end: create a request as `fund_demo`, approve
it as `gm_demo`, then finalize as `md_demo`.

## Documentation

See [`docs/`](docs/) for architecture, business rules, the dev plan and the test
plan.
