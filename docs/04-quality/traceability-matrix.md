# Traceability Matrix

Maps every PDF requirement → where it's designed → where it's built → where it's tested.
Keep this current; it's the fastest way for a reviewer (and you, in the interview) to verify coverage.

## Requirements → design → phase → test
| PDF § | Requirement | Business rule | Built in phase | Test |
|-------|-------------|---------------|----------------|------|
| §2 | Fund accounts + incoming funds; unique txn ref; confirm→unassigned | BR-05/06/07/08 | Phase 1 | test_incoming |
| §3 | Allocation project XOR head; hold/assign/release; block over-allocate | BR-09/10/11/12 | Phase 3 | test_allocation |
| §4 | GM→MD order; current approver; no self-approval; configurable; idempotent; history | BR-13..17, BR-03 | Phase 2 | test_approval |
| §5 | Project/head computed balances; no manual edit; no negatives | BR-18/19/04 | Phase 4 | test_balances |
| §6 | Requisition hold/reserve/release; remaining billable; close | BR-20..23 | Phase 5 | test_requisition |
| §7 | Bills vs approved req; same bucket; partial; over-bill block; reverse no-funds; cross-project block | BR-24..30 | Phase 6 | test_bill |
| §8 | Transfer hold/move/return; source≠dest; over-transfer block; held unusable | BR-31..34, BR-02 | Phase 7 | test_transfer |
| §9 | Groups, ACLs, record rules, server-side, multi-company | BR-35..38 | Phase 8 | test_security |
| §10 | Audit history; no delete of confirmed records | BR-39/40 | Phase 9 | test_balances/security (unlink) |
| §11 | Bonus: approval rules, bank email, dashboard | — | Phase 11 | (bonus tests) |
| §13 | Sample demonstration 1–13 | BR-01..30 | Phases 1–7 | test_demo_scenario |
| §14 | Technical expectations (constraints, computed, no hardcoded IDs, no manual balances) | BR-01/03/04/16/18 | All | all |

## Evaluation areas (§15) → evidence
| Evaluation area | Evidence |
|-----------------|----------|
| Business logic & workflow accuracy | state-machines.md, test_approval, test_demo_scenario |
| Balance calculation & data integrity | ADR-0001 ledger, test_balances, conservation helper |
| Prevention of double spending | double-spend matrix in test-plan, BR-02/03 |
| Odoo model & module structure | architecture.md §7, models-spec.md |
| Security & access control | security-matrix.md, test_security |
| Approval workflow implementation | nn.approval.mixin, test_approval |
| Automated test quality | this matrix + test-plan.md (every BR covered) |
| Code readability & maintainability | reusable mixin, ledger uniformity, ADRs |
| Documentation quality | this docs/ set |
| AI usage transparency | 05-ai-usage/ai-usage-log.md |
| Ability to explain & modify | ADRs + interview-prep answers below |

## Interview-readiness (§16) — where each answer lives
| They may ask | Point to |
|--------------|----------|
| How balances are calculated | ADR-0001 + architecture.md §5 (sum over ledger) |
| How double spending is prevented | hold lines + idempotent posting (BR-02/03) |
| Add/remove an approval level | nn.approval.mixin level list / nn.approval.rule |
| Change an approval rule | nn.approval.rule (Phase 11) |
| What happens when a bill is cancelled | reverse line restores remaining_billable (BR-30) |
| Fix a workflow issue | state-machines.md transition table |
| Add a new automated test | test-plan.md structure |
| How unauthorized approval is blocked | _check_approver() + security-matrix |
| Pending transfer funds cannot be used | transfer hold (BR-02), test_transfer |
| Live modification | small, localized via mixin/ledger design |
