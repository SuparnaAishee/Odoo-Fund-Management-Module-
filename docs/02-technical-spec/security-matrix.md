# Security Matrix

## Groups (`security/groups.xml`)
| Group | XML id | Inherits | Purpose |
|-------|--------|----------|---------|
| Fund User | `group_fund_user` | base.group_user | Create/view own allowed requests |
| Finance User | `group_finance_user` | group_fund_user | Confirm incoming funds, financial ops |
| GM Approver | `group_gm_approver` | base.group_user | First approval level |
| MD Approver | `group_md_approver` | base.group_user | Final approval level |
| Fund Administrator | `group_fund_admin` | group_finance_user | Full config + cancellations |

> GM/MD are orthogonal to the user hierarchy (an approver may not be a Finance user).
> Approvers are resolved from these groups / `nn.approval.rule` — never hardcoded IDs (BR-16).

## ACL grid (`ir.model.access.csv`) — C/R/U/D
| Model | Fund User | Finance User | GM/MD Approver | Fund Admin |
|-------|-----------|--------------|----------------|------------|
| nn.fund.account | R | R | R | CRUD |
| nn.incoming.fund | R | CRU | R | CRUD |
| nn.fund.allocation | CR (own) | CRU | R | CRUD |
| nn.fund.requisition | CR (own) | CRU | R | CRUD |
| nn.fund.bill | CR | CRU | R | CRUD |
| nn.fund.transfer | CR (own) | CRU | R | CRUD |
| nn.fund.movement | R | R | R | R (no manual write — immutable) |
| nn.approval.line | R | R | RU (own decisions) | CRUD |
| nn.project / nn.expense.head | R | R | R | CRUD |
| nn.approval.rule | – | R | R | CRUD |

> No group gets Delete on confirmed financial records via UI; `unlink` is overridden to block
> deletion of posted/confirmed records (BR-40). Movement `write`/`unlink` blocked for everyone.

## Record rules (`security/record_rules.xml`)
| Rule | Model | Domain | BR |
|------|-------|--------|----|
| Multi-company | all financial models | `['|',('company_id','=',False),('company_id','in',company_ids)]` | BR-37 |
| Own requests (Fund User) | allocation/requisition/transfer | `[('requested_by','=',user.id)]` for read/write when only group_fund_user | BR-35 |
| Finance confirm | incoming.fund confirm action | server check `group_finance_user` | BR-08 |

## Server-side enforcement (not UI-only) — BR-38
- `action_confirm` (incoming) asserts `group_finance_user`.
- `action_approve/reject` call `_check_approver()`: current level + approver group + no self-approval (BR-13..15).
- `action_cancel` on approved records asserts authorized group (BR-36).
- Balance/ledger writes only via posting methods; `nn.fund.movement.write/unlink` raise.
- All checks live in Python methods + `@api.constrains`, independent of button visibility.

## Tests proving security (Phase 10)
Use `self.env(user=...)` / `with_user` to assert that a Fund User cannot approve, a non-Finance
user cannot confirm incoming funds, and cross-company records are invisible.
