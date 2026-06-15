# State Machines & Fund-Flow

## 1. Shared approval workflow (allocation, requisition, transfer)

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> submitted : action_submit  (validate + post HOLD)
    submitted --> gm_approval : GM approves
    submitted --> rejected : GM rejects   (post RELEASE)
    gm_approval --> md_approval : MD approves
    gm_approval --> rejected : MD rejects  (post RELEASE)
    md_approval --> approved : final       (post ASSIGN / reserve / TRANSFER_IN)
    draft --> cancelled
    submitted --> cancelled : (post RELEASE)
    gm_approval --> cancelled : (post RELEASE)
    rejected --> [*]
    cancelled --> [*]
    approved --> [*]
```

> Requisition adds one terminal state: `approved --> closed` (fully billed or unused released).
> Guards: MD cannot act before GM (BR-13); only current-level approver acts (BR-14);
> no self-approval (BR-15); each transition posts ledger lines once (BR-03).

## 2. Money flow through a bucket's lifetime

```mermaid
flowchart LR
    A[Account: received] -->|confirm incoming| U[Account: unassigned]
    U -->|allocation submit| H1[Allocation HOLD]
    H1 -->|approve| AS[Project/Head: assigned/available]
    H1 -->|reject/cancel| U
    AS -->|requisition submit| H2[Requisition HOLD]
    H2 -->|approve| R[Reserved for bills]
    H2 -->|reject/cancel| AS
    R -->|bill posted| S[Spent]
    R -->|close unused| AS
    S -->|bill reversed| R
    AS -->|transfer submit| H3[Transfer HOLD - source]
    H3 -->|approve| D[Destination bucket available]
    H3 -->|reject/cancel| AS
```

## 3. Bill lifecycle

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> posted : validate (approved req, same bucket, ≤ remaining billable) → post SPEND
    posted --> cancelled : reverse → post REVERSE (returns to remaining billable, creates no funds)
    draft --> cancelled
```

## 4. Invariant checks fired on each transition
| Transition | Checks (BR refs) |
|------------|------------------|
| allocation submit | amount ≤ account unassigned (BR-10), project XOR head (BR-09) |
| any approve/reject | level order (BR-13), current approver (BR-14), no self-approve (BR-15), idempotent (BR-03) |
| requisition submit | amount ≤ bucket available (BR-20) |
| bill post | approved req (BR-24), same bucket (BR-25/28), ≤ remaining billable (BR-26), total ≤ approved (BR-27) |
| transfer submit | amount ≤ source available (BR-31), source ≠ dest (BR-34) |
| any | resulting balance ≥ 0 (BR-04), no funds created (BR-01) |
