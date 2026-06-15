# Business Rules — enforceable invariants

Every rule below is **server-side enforced** (`@api.constrains`, workflow guards, or record
rules) — never UI-only. IDs (BR-xx) are referenced by the test plan and traceability matrix.

## Money conservation & double-spend
- **BR-01** No action may create funds. Reversals/cancellations post compensating ledger lines only.
- **BR-02** Held funds (allocation hold, requisition hold, transfer hold) cannot be allocated, requisitioned, transferred or spent again.
- **BR-03** Repeated approval/transition actions must not post duplicate fund movements (idempotent, guarded by state + `posted` flag).
- **BR-04** No balance may go negative (account unassigned, project/head available, remaining billable).

## Incoming funds (PDF §2)
- **BR-05** Amount must be > 0.
- **BR-06** `(fund_account, transaction_reference)` must be unique — same reference cannot be used twice in the same account.
- **BR-07** Only after confirmation does the amount enter the account's unassigned balance.
- **BR-08** Only authorized Finance users may confirm incoming funds.

## Allocation (PDF §3)
- **BR-09** A request targets a project **XOR** an expense head — exactly one, never both, never neither.
- **BR-10** On submit: amount ≤ account available unassigned, else block; move amount to **hold**.
- **BR-11** On approve: hold → **assigned** under the chosen project/head.
- **BR-12** On reject/cancel: amount returns to unassigned.

## Approval (PDF §4)
- **BR-13** GM approval must complete before MD; MD cannot approve before GM.
- **BR-14** Only the current-level approver may approve/reject.
- **BR-15** A user cannot approve their own request unless explicitly authorized.
- **BR-16** Approvers are resolved from security groups / rules — **no hardcoded user or DB IDs**.
- **BR-17** Every decision records approver, date, level, comment and result.

## Project / expense-head balances (PDF §5)
- **BR-18** Balance fields are **computed** (sum over ledger); never manually editable.
- **BR-19** Identity: `allocated = available + requisition_hold + transfer_hold + approved_unspent + spent + (outgoing − incoming) transfers` (reconciles to ledger).

## Requisition (PDF §6)
- **BR-20** On submit: requested amount ≤ available project/head balance; place on **requisition hold**.
- **BR-21** On approve: amount stays **reserved** for bills; `remaining_billable = approved amount`.
- **BR-22** On reject/cancel: amount returns to available balance.
- **BR-23** Closeable when fully billed **or** unused amount released.

## Bills (PDF §7)
- **BR-24** A bill must link to an **approved** requisition.
- **BR-25** Bill's project/head must match the requisition's.
- **BR-26** A bill cannot exceed the requisition's remaining billable amount.
- **BR-27** Multiple partial bills allowed; total billed ≤ approved amount.
- **BR-28** Project A cannot use Project B's requisition; one head cannot use another head's requisition.
- **BR-29** Posting a bill marks the amount **spent** and decreases remaining billable.
- **BR-30** Cancelling/reversing a posted bill returns the amount to remaining billable and creates no new funds.

## Transfer (PDF §8)
- **BR-31** On submit: amount ≤ source available; place on **transfer hold** (deduct from source available).
- **BR-32** On approve: amount added to destination balance.
- **BR-33** On reject/cancel: amount returns to source.
- **BR-34** Source ≠ destination.

## Security (PDF §9)
- **BR-35** Fund Users create/view allowed requests only.
- **BR-36** Only assigned approvers approve/reject; only authorized users cancel approved transactions.
- **BR-37** Users cannot access another company's records (record rules).
- **BR-38** All of the above are checked server-side; hiding buttons is insufficient.

## Audit (PDF §10)
- **BR-39** History records creator, submitter, approver/rejecter, prev→new status, datetime, comment, amount, related account, related project/head, reference doc.
- **BR-40** Confirmed financial records cannot be deleted without cancellation/reversal (override `unlink`).
