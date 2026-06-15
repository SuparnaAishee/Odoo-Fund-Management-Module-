# Business Requirements Document (BRD) — Fund Management

**Module:** `nn_fund_management` · **Client:** NN Services & Engineering Ltd. · **Currency:** BDT

## 1. Problem statement
NN receives money into bank/cash accounts and needs to control how every taka is allocated,
held, spent and transferred — with two-level management approval — so that **the same money
can never be allocated, transferred or spent more than once**. Today this is untracked; the
module must make every balance explainable and every financial action auditable.

## 2. Goals
- Record incoming funds and track an account's **received / unassigned / held / assigned** balances.
- Allocate unassigned funds to a **project or an expense head** (never both) via approval.
- Track per-project / per-head balances: allocated, available, holds, approved-unspent, spent, transfers.
- Raise **requisitions** against a project/head and **bills** against approved requisitions (partial billing).
- **Transfer** funds between any project/head pair.
- Enforce a **GM → MD** approval chain (configurable, not hardcoded).
- Preserve a full **audit history**; prevent deletion of confirmed financial records.

## 3. Actors
| Actor | Responsibility |
|-------|----------------|
| Fund User | Creates and views allowed requests (allocations, requisitions, transfers, bills). |
| Finance User | Confirms incoming funds; authorized financial operations. |
| GM Approver | First approval level. |
| MD Approver | Second/final approval level (only after GM). |
| Fund Administrator | Full configuration: accounts, heads, approval rules, cancellations. |

## 4. Scope
**In scope (MUST):** fund accounts + incoming funds, allocation, project/head balances, GM/MD
approval, security, automated tests.
**In scope (SHOULD):** requisition, bills, transfers, audit history.
**Bonus:** configurable approval-rule engine, bank-email ingestion, dashboard + notifications.
**Out of scope:** full accounting integration (GL postings), payroll, procurement, FX.

## 5. Core invariant (the reason the module exists)
> Money is conserved. The sum of (unassigned + held + assigned + spent + in-transit) never
> changes except by a recorded *incoming* event. No action may create funds; reversals are
> compensating entries only.

This invariant is enforced through the **Fund Movement Ledger** — see
[ADR-0001](../01-architecture/adr/0001-fund-movement-ledger.md).

## 6. Success criteria (from the PDF rubric §15)
Business-logic accuracy · balance integrity · double-spend prevention · clean Odoo structure ·
security · approval workflow · automated-test quality · maintainability · documentation ·
AI-usage transparency · ability to explain/modify the solution.

## 7. Key assumptions
- Single currency (BDT); multi-company supported via `company_id` + record rules.
- Projects are modeled as a **light custom `nn.project`** (see [ADR-0002](../01-architecture/adr/0002-custom-project-model.md)).
- Bills use a **custom `nn.fund.bill`** model rather than `account.move` (see [ADR-0003](../01-architecture/adr/0003-custom-bill-model.md)).
- Approval levels default to GM then MD, overridable by the bonus rule engine.

See [`business-rules.md`](business-rules.md) for the enforceable rules and [`glossary.md`](glossary.md) for terms.
