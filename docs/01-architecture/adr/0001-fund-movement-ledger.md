# ADR-0001: Append-only Fund Movement Ledger

**Status:** Accepted · **Date:** 2026-06-15

## Context
The assessment is graded on (a) "the same money cannot be allocated, transferred or spent more
than once", (b) "balance fields calculated automatically, users must not manually edit them",
(c) a clear audit history, and (d) reversals that "must not create additional funds". We need a
single data design that satisfies all four without scattering balance arithmetic across models.

## Decision
Introduce one immutable model, `nn.fund.movement`, where every atomic money event is a row:
`(date, move_type, amount, from_bucket, to_bucket, origin_model, origin_id, state)`.
Move types: `incoming, hold, release, assign, spend, transfer_in, transfer_out, reverse`.

- **All** balance fields on accounts/projects/heads are **computed sums** over movements.
- Workflow methods **post movement lines**; they never write a balance field.
- Each workflow transition is **idempotent** (guarded by state + a `posted` flag) so repeated
  actions cannot double-post.
- Cancellations/reversals post **compensating** lines; no line is ever edited or deleted.

## Consequences
**Positive**
- Double-spend is structurally hard: a hold line removes availability until released.
- Balances are never hand-editable (they're computed) — satisfies §5/§14 directly.
- The ledger *is* the audit trail (§10); any balance drills down to its lines.
- Reversal-as-compensation guarantees funds are never created (§7).

**Negative / mitigations**
- Computed sums over many rows can be slow → store computed fields with correct `@api.depends`
  and/or use `read_group`; index `(from_bucket, to_bucket, move_type, state)`.
- More rows than a mutable-balance design → acceptable; rows are cheap and audit-valuable.

## Alternatives rejected
- **Mutable balance columns** updated in workflow code: fragile, easy to double-apply, fails the
  "no manual edit / no duplicate movement" requirements, and gives no audit trail.
