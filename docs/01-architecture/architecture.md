# Architecture — nn_fund_management

> This is also the "short architecture explanation" deliverable (PDF #5). Odoo 17 Community.

## 1. Big picture
A single Odoo addon. All financial state derives from one **append-only ledger**
(`nn.fund.movement`); balances are computed sums over ledger lines, never hand-edited.
Three transaction types (allocation, requisition→bill, transfer) share **one reusable
approval engine** (`nn.approval.mixin`). Security is enforced by groups + ACLs + record rules.

```
                ┌─────────────────────────────────────────────┐
                │              nn.approval.mixin               │
                │  draft→submitted→gm→md→approved/rejected/...  │
                │  + nn.approval.line (history) + mail.thread   │
                └───────▲───────────────▲───────────────▲──────┘
                        │               │               │
              nn.fund.allocation  nn.fund.requisition  nn.fund.transfer
                        │               │               │
                        │           nn.fund.bill        │
                        │               │               │
                        ▼               ▼               ▼
                ┌─────────────────────────────────────────────┐
                │      nn.fund.movement  (append-only ledger)   │
                │  type, amount, from_bucket, to_bucket, state  │
                └───────▲───────────────▲───────────────▲──────┘
                        │ computed sums  │               │
              nn.fund.account      nn.project      nn.expense.head
                        ▲
                  nn.incoming.fund
```

## 2. Layers
| Layer | Models | Role |
|-------|--------|------|
| Master data | `nn.fund.account`, `nn.project`, `nn.expense.head` | Buckets that hold balances. |
| Money-in | `nn.incoming.fund` | Records deposits; confirm → posts `incoming`. |
| Ledger (spine) | `nn.fund.movement` | Immutable atomic money events; source of all balances. |
| Workflow engine | `nn.approval.mixin`, `nn.approval.line` | Reusable GM→MD state machine + history. |
| Transactions | `nn.fund.allocation`, `nn.fund.requisition`, `nn.fund.bill`, `nn.fund.transfer` | Business actions that post ledger lines. |
| Config (bonus) | `nn.approval.rule` | Amount-band / type-based approval chains. |
| Security | groups, `ir.model.access.csv`, `ir.rule` | Server-side access control. |

## 3. The ledger pattern (core decision — ADR-0001)
Each money event is one immutable row: `(date, type, amount, from_bucket, to_bucket,
origin_model, origin_id, state)`. Types: `incoming, hold, release, assign, spend,
transfer_out, transfer_in, reverse`.

- **Balances = `read_group`/`sum` over movements**, computed fields, store=True with proper
  `@api.depends` (or recompute triggers) for list-view performance.
- **Workflow actions post lines; they never write a balance.** This is what guarantees
  "no manual editing of calculated balances" (PDF §14) and "balances calculated automatically" (§5).
- **Idempotency:** each transition checks a `posted` guard so re-clicking Approve cannot
  double-post (PDF §4 "repeated approval actions do not create duplicate fund movements").
- **Reversal = compensating line**, so funds are never created (PDF §7).

See [`erd.md`](erd.md) for entities/relations and [`state-machines.md`](state-machines.md) for workflows.

## 4. Reusable approval engine
`nn.approval.mixin` (AbstractModel, inherits `mail.thread`, `mail.activity.mixin`) provides:
`action_submit / action_approve / action_reject / action_cancel`, current-level resolution,
self-approval guard, and abstract hooks `_post_on_submit() / _post_on_approve() /
_post_on_reject()` that each concrete model implements to post its own ledger lines.
Approvers come from security groups (default GM→MD) or, with the bonus, from `nn.approval.rule`.

## 5. Balance formulas (per bucket)
- Account: `unassigned = Σincoming − Σ(hold+assign out of account)`, `on_hold`, `assigned`, `received`.
- Project/Head: `allocated = Σassign(in)`; `available = allocated + transfers_in − transfers_out − req_hold − transfer_hold − spent`; `approved_unspent = Σ approved-requisition reserved − spent`; plus `requisition_hold`, `transfer_hold`, `spent`, `incoming/outgoing transfers`.
Exact field-level spec in [`../02-technical-spec/models-spec.md`](../02-technical-spec/models-spec.md).

## 6. Security model
Groups: Fund User ⊂ Finance User ⊂ Fund Administrator (config), plus GM Approver, MD Approver
as orthogonal approval groups. ACLs per model + record rules for multi-company and
"see only allowed requests". Full grid in [`../02-technical-spec/security-matrix.md`](../02-technical-spec/security-matrix.md).

## 7. Module file layout
```
nn_fund_management/
├── __manifest__.py
├── models/        (account, project, expense_head, incoming_fund, movement,
│                   approval_mixin, approval_line, allocation, requisition, bill,
│                   transfer, approval_rule)
├── views/         (one xml per model + menus.xml)
├── security/      (groups.xml, ir.model.access.csv, record_rules.xml)
├── data/          (ir.sequence, expense head seeds)
├── tests/         (test_balances, test_approval, test_allocation, test_bill,
│                   test_transfer, test_security, test_demo_scenario)
└── static/description/  (icon, index.html)
```

## 8. Key trade-offs (ADRs)
- [ADR-0001](adr/0001-fund-movement-ledger.md): append-only ledger vs. mutable balance fields.
- [ADR-0002](adr/0002-custom-project-model.md): custom `nn.project` vs. reuse `project.project`.
- [ADR-0003](adr/0003-custom-bill-model.md): custom `nn.fund.bill` vs. `account.move`.
