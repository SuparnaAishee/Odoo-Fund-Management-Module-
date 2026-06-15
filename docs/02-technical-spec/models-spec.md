# Technical Spec — Models, Fields, Constraints

Conventions: monetary fields use `currency_id` (company currency); all transaction models inherit
`nn.approval.mixin`; sequences via `ir.sequence`; bucket = project XOR expense head.

## `nn.fund.movement` (ledger — immutable)
| Field | Type | Notes |
|-------|------|-------|
| `date` | Datetime | default now |
| `move_type` | Selection | incoming/hold/release/assign/spend/transfer_in/transfer_out/reverse |
| `amount` | Monetary | > 0 |
| `account_id` | Many2one `nn.fund.account` | set for account-side moves |
| `project_id` | Many2one `nn.project` | nullable |
| `expense_head_id` | Many2one `nn.expense.head` | nullable |
| `origin_model` / `origin_id` | Char / Integer | source document (or use `reference`) |
| `state` | Selection | mirrors origin state for filtering |
- **Immutable:** override `write`/`unlink` to forbid changes once created (audit integrity, BR-40).
- **Indexes:** `(account_id, move_type)`, `(project_id, move_type)`, `(expense_head_id, move_type)`.

## `nn.fund.account`
| Field | Type | Notes |
|-------|------|-------|
| `name`, `code` | Char | |
| `account_type` | Selection | bank/cash/other |
| `company_id` | Many2one | default env company |
| `currency_id` | Many2one | |
| `received` | Monetary (computed, stored) | Σ incoming |
| `unassigned` | Monetary (computed, stored) | received − Σ(hold+assign out) |
| `on_hold` | Monetary (computed, stored) | Σ active holds |
| `assigned` | Monetary (computed, stored) | Σ assign |
- Constraint: `unassigned >= 0` (BR-04).

## `nn.incoming.fund`
| Field | Type | Notes |
|-------|------|-------|
| `name` | Char | seq `INF/####` |
| `fund_account_id` | Many2one | required |
| `date` | Date | |
| `amount` | Monetary | > 0 (BR-05) |
| `transaction_reference` | Char | |
| `sender`, `description` | Char/Text | |
| `attachment_ids` | Many2many `ir.attachment` | |
| `company_id` | Many2one | |
| `state` | Selection | draft/confirmed |
- **SQL constraint:** `UNIQUE(fund_account_id, transaction_reference)` (BR-06).
- `action_confirm` → post `incoming` movement (BR-07); Finance-only (BR-08).

## `nn.project` / `nn.expense.head`
Computed-stored monetary fields (sum over ledger): `allocated, available, requisition_hold,
transfer_hold, approved_unspent, spent, transfer_in, transfer_out` (head may omit hold-detail if
simpler, but keep `allocated/available/spent`). All read-only (BR-18). Constraint `available >= 0`.

## `nn.approval.mixin` (AbstractModel)
Fields: `state` (draft/submitted/gm_approval/md_approval/approved/rejected/cancelled),
`current_level` (computed), `approval_line_ids` (One2many `nn.approval.line`), `requested_by`,
`posted` (Boolean guard). Inherits `mail.thread`, `mail.activity.mixin`.
Methods: `action_submit/approve/reject/cancel`; abstract `_post_on_submit/_on_approve/_on_reject`;
`_check_approver()` (level + current-approver + self-approval guards, BR-13..15).

## `nn.approval.line`
`approver_id` (Many2one res.users), `decision_date` (Datetime), `level` (gm/md/finance),
`result` (approved/rejected), `comment` (Text), plus `res_model`/`res_id` or reverse One2many.

## `nn.fund.allocation`
`name` (seq `ALLOC/####`), `fund_account_id`, `project_id`, `expense_head_id`, `amount`,
`purpose`, `request_date`, `requested_by`, `attachment_ids`, + mixin state/history.
- Constraint: exactly one of project/head (BR-09); `amount <= fund_account_id.unassigned` on submit (BR-10).
- Hooks: submit→`hold`; approve→`assign`; reject/cancel→`release`.

## `nn.fund.requisition`
`name` (seq `REQ/####`), `project_id`/`expense_head_id`, `amount`, `purpose`, `request_date`,
`required_date`, `requested_by`, `attachment_ids`, `remaining_billable` (computed), state (+`closed`).
- submit→`hold` (≤ bucket available, BR-20); approve→reserve; reject/cancel→`release`; `action_close` (BR-23).

## `nn.fund.bill`
`name` (seq `BILL/####`), `requisition_id` (required), `amount`, `state` (draft/posted/cancelled).
- Validate (BR-24..28): approved req; same bucket; `amount <= requisition_id.remaining_billable`; total ≤ approved.
- post→`spend`; cancel→`reverse` (BR-29/30).

## `nn.fund.transfer`
`name` (seq `TRF/####`), source (`src_project_id`/`src_head_id`), dest (`dest_project_id`/`dest_head_id`),
`amount`, `reason`, `requested_by`, `request_date`, + mixin.
- Constraints: source ≠ dest (BR-34); `amount <= source.available` (BR-31).
- submit→`transfer_out` hold; approve→`transfer_in`; reject/cancel→`release`.

## `nn.approval.rule` (bonus)
`request_type` (allocation/requisition/transfer), `amount_min`, `amount_max`, `company_id`,
`category`, `sequence`, `group_id`. Engine picks matching rule to build the approver chain.
