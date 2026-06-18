# NN Fund Management (Odoo 17)

Allocate, hold, requisition, bill and transfer funds with a **GM → MD** approval
chain, built on an append-only fund-movement ledger. Every balance is a computed
sum over the immutable `nn.fund.movement` ledger — no balance is ever edited by
hand, so the same money can never be allocated, transferred or spent twice.

## Odoo version

- **Odoo 17.0** (Community), Python 3.10, PostgreSQL 15.
- Pinned via the `odoo:17.0` and `postgres:15` Docker images in `docker-compose.yml`.

## Required dependencies

- **Odoo modules:** `base`, `mail` (declared in `__manifest__.py`). `mail` powers
  the chatter, approval-tracking messages and the To-Do activities raised for
  approvers. No other addons are required.
- **System:** Docker + Docker Compose (the only thing you install locally). The
  images bundle Python and every Python library Odoo needs — there are no extra
  `pip` requirements.

## Installation

```bash
docker compose up -d
```

Then open http://localhost:8069 and select database **`nn_test`**.

To (re)install or update the module after code changes:

```bash
docker compose run --rm odoo odoo -d nn_test -u nn_fund_management --stop-after-init
```

If the `nn_test` database does not exist yet, create and install in one step:

```bash
docker compose run --rm odoo odoo -d nn_test -i nn_fund_management --stop-after-init
```

## Configuration steps

1. **Approvers are data, not hardcoded.** Assign users to the **GM Approver** and
   **MD Approver** groups (Settings → Users) to decide who approves each level.
   The demo users below are pre-assigned.
2. **Approval rules (optional).** Fund Management → Configuration → Approval Rules
   lets you define amount-band chains per request type (e.g. up to 50,000 → GM
   only; above 200,000 → GM + MD). Seed rules ship in
   `data/approval_rule_data.xml`; edit or add bands without touching code.
3. **Expense heads** are seeded (`data/expense_head_data.xml`: office rent, salary,
   utilities, marketing, administrative). Add more under Configuration.
4. **Outgoing mail** is optional — workflow tracking mails are *queued*, not
   force-sent, so a missing mail server never blocks an approval.

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

## Testing instructions

The module ships 48 automated tests (allocation, approval, approval rules,
balances, bills, incoming funds, requisitions, security, transfers, plus the
full PDF demo scenario). Run them with:

```bash
docker compose run --rm odoo odoo -d nn_test -u nn_fund_management \
  --test-enable --stop-after-init
```

A clean run ends with `0 failed, 0 error(s) of 48 tests`. Test sources live in
`addons/nn_fund_management/tests/`; `test_demo_scenario.py` reproduces the
section-13 walkthrough (receive 1,000,000 → allocate → reject → re-approve →
transfer → requisition → partial bill → over-bill block).

## Security groups

Operational hierarchy (each implies the one below): **Fund User** → **Finance
User** → **Fund Administrator**. Approval groups (**GM Approver**, **MD
Approver**) are orthogonal — an approver need not be a finance user. Access is
enforced server-side with ACLs (`ir.model.access.csv`), record rules
(`record_rules.xml`) and Python guards, not just hidden UI buttons.

## Architecture (short)

The spine is an **append-only ledger**, `nn.fund.movement`: every money event
(incoming, hold, release, assign, spend, transfer_in/out, reverse) is one
immutable line. **All balances are `sum()` computations over that ledger** —
never stored-and-mutated — so they are always explainable by drilling into the
lines (this *is* the audit history). Double-spend is prevented by **idempotent
posting**: each workflow action posts its lines at most once, guarded by state +
a `posted` flag, so repeated approvals never duplicate fund movements. The GM→MD
workflow lives in a reusable `ApprovalMixin` shared by allocations, requisitions
and transfers. See [`docs/`](docs/) for the full architecture, ERD, state
machines, model spec, security matrix and AI-usage log.

## Assumptions

- Single currency (BDT); the company currency is used for all amounts and
  rounding comparisons.
- Two mandatory approval levels (GM → MD) by default; the approval-rule engine
  can shorten/extend the chain per amount band, but GM-before-MD ordering is
  enforced.
- A transaction targets **either** a project **or** an expense head, never both.
- Demo users and seed data are for evaluation; real deployments reassign the
  approver groups and remove the demo accounts.
- Bills are modelled with a custom `nn.fund.bill` (linked to an approved
  requisition) rather than Odoo Vendor Bills, to keep the fund-control rules
  self-contained.

## Known limitations

- **Bank Email Integration (bonus §12) is not implemented** — no email-parsing
  prototype ships in this submission.
- Multi-currency is out of scope (single-company, single-currency assumption).
- Approval-rule matching is by amount band + request type; per-project or
  per-category routing is seeded but not exhaustively tested.
- The "almost fully billed" alert posts to chatter at ≤10% remaining; the
  threshold is a constant, not yet a configuration field.

## Documentation

See [`docs/`](docs/) for architecture, business rules, the dev plan and the test
plan.
