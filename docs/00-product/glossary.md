# Glossary

| Term | Meaning |
|------|---------|
| **Fund Account** | A bank, cash or other financial account that receives money. Tracks received/unassigned/held/assigned. |
| **Incoming Fund** | A recorded deposit into a fund account; on confirmation it raises the account's unassigned balance. |
| **Unassigned balance** | Money received but not yet allocated to any project or expense head. |
| **Expense Head** | A spending category (Office rent, Salary, Utilities, Marketing, Administrative). |
| **Project** | A work unit funds can be assigned to (custom `nn.project`). |
| **Bucket** | Generic term for "a project or an expense head" — the destination of allocations/transfers. |
| **Allocation** | Moving unassigned account funds to a project/head, via approval. |
| **Hold** | Money reserved by a pending request; unavailable for any other use. Three kinds: allocation hold, requisition hold, transfer hold. |
| **Assigned** | Funds approved into a project/head and available there. |
| **Requisition** | A request to draw funds from a project/head's available balance, reserved for bills once approved. |
| **Remaining billable** | Approved requisition amount minus amounts already billed against it. |
| **Bill** | A spend document against an approved requisition; reduces remaining billable and increases spent. |
| **Transfer** | Moving funds between two buckets (project/head → project/head). |
| **Spent** | Funds consumed by posted bills (terminal state of money). |
| **Fund Movement** | An immutable ledger line recording one atomic money event (see ADR-0001). |
| **Approval level** | A stage in the chain (GM, MD, optionally Finance). |
| **GM / MD** | General Manager / Managing Director — the two minimum approval levels. |
| **Posted (guard)** | A flag/state ensuring a transition's ledger lines are written at most once (idempotency). |
| **Reversal** | A compensating ledger entry that undoes a prior spend/transfer without creating new funds. |
| **Record rule** | Odoo row-level access control (`ir.rule`), e.g. multi-company isolation. |
| **ACL** | `ir.model.access.csv` — model-level CRUD permissions per group. |
