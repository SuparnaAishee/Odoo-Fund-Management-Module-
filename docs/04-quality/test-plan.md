# Test Plan

**Framework:** Odoo `TransactionCase` (+ `tagged('post_install','-at_install')`).
**Run:** `odoo -i nn_fund_management --test-enable --stop-after-init` (or `--test-tags nn_fund_management`).
**Principle:** every Business Rule (BR-xx) and every Sample-Demo step (§13) has a test.

## Test files & coverage
| File | Covers | BR / PDF |
|------|--------|----------|
| `test_incoming.py` | confirm raises unassigned; amount>0; duplicate txn ref blocked | BR-05/06/07, §2 |
| `test_balances.py` | computed account & bucket balances reconcile to ledger; no negatives | BR-04/18/19, §5 |
| `test_approval.py` | GM-before-MD; MD-before-GM blocked; only current approver; no self-approval; idempotent double-approve posts once | BR-03/13/14/15, §4 |
| `test_allocation.py` | project XOR head; over-allocation blocked; hold→assign→release flows | BR-09/10/11/12, §3 |
| `test_requisition.py` | hold on submit; reserve on approve; release on cancel; remaining_billable; close | BR-20..23, §6 |
| `test_bill.py` | approved-req only; same bucket; partial bills; over-bill blocked; total≤approved; reverse restores, creates no funds; cross-project blocked | BR-24..30, §7 |
| `test_transfer.py` | source≠dest; over-transfer blocked; held funds unusable; approve moves to dest | BR-31..34, §8 |
| `test_security.py` | `with_user`: Fund User cannot approve; non-Finance cannot confirm; cross-company invisible | BR-35..38, §9 |
| `test_demo_scenario.py` | end-to-end replay of §13 steps 1–13 as one test | §13 (all) |

## Double-spend test matrix (the headline grade — BR-02/03)
| Scenario | Expected |
|----------|----------|
| Allocate held funds again | ValidationError (insufficient unassigned) |
| Requisition more than available (some on hold) | ValidationError |
| Transfer funds already on transfer hold | ValidationError |
| Click Approve twice | exactly one set of movements (assert ledger line count) |
| Reverse a bill | remaining_billable restored; total funds unchanged (assert conservation) |

## `test_demo_scenario.py` outline (§13)
1. Receive 1,000,000 → account unassigned == 1,000,000.
2. Allocate 600,000 to Project A, submit → unassigned 400,000, hold 600,000.
3. Assert held while pending.
4. Reject → unassigned back to 1,000,000.
5. Re-submit + GM + MD approve → Project A available 600,000.
6. Transfer 200,000 A→B, submit → A available 400,000, transfer hold 200,000.
7. Assert held while pending.
8. Approve → B available 200,000.
9. Requisition 150,000 on B, approve → B requisition reserved 150,000.
10. Bill 100,000 → remaining_billable 50,000, B spent 100,000.
11. Assert remaining_billable == 50,000.
12. Bill 60,000 → ValidationError.
13. Use B's requisition from Project A → ValidationError.

## Conservation assertion (reusable helper)
After every test, assert: `Σ incoming == unassigned + on_hold + assigned_available + reserved + spent + in_transit`
across all accounts/buckets — proves BR-01 (no funds created/destroyed).

## Definition of "green"
All tests pass on a clean DB install; the demo scenario passes as a single test; coverage of
every BR row above. CI optional but recommended (GitHub Actions running the test command in the Docker image).
