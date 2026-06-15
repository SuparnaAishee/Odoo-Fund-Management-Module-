# Development Plan — nn_fund_management

**Goal:** build the Odoo Fund Management module in dependency order, one phase at a time.
Each phase is independently demonstrable and leaves the module **installable and green**
(it installs, no traceback, existing tests pass). Do not start a phase until the previous
phase installs cleanly.

- **Target Odoo version:** 17.0 (Community) — **locked**. Pin everywhere (Docker, manifest, README).
- **Project model:** light custom `nn.project` — **locked** (self-contained, no `project` dependency coupling).
- **Module name:** `nn_fund_management`
- **Deadline:** 22 June 2026, 23:59
- **Spine pattern:** the Fund Movement Ledger (see `docs/README.md`). Every phase posts ledger lines; nothing mutates a balance by hand.

## How to use this document

Work top to bottom. For each phase: read **Goal → Build → Acceptance → Maps to PDF**, do it,
commit with a meaningful message, tick the box, move on. The **Definition of Done** at the
bottom applies to *every* phase.

---

## Priority & time budget (if time runs short)

The PDF says full completion is **not** mandatory — they grade approach, prioritization, and the
core integrity logic. So lock the **MUST** band first; treat **BONUS** as overflow.

| Band | Phases | Why |
|------|--------|-----|
| **MUST** (core grade) | 0, 1, 2, 3, 4, 8, 10 | Installable module + balances + reusable approval + allocation + security + tests. This alone is a strong submission. |
| **SHOULD** | 5, 6, 7, 9 | Requisition, bills, transfers, audit. Completes the business story + the Sample Demo §13. |
| **BONUS** | 11 (rules engine, bank email, dashboard) | Extra credit only — never at the expense of MUST. |
| **ALWAYS** | 12 (docs, video, deploy) | Required deliverables; reserve the last day for these. |

---

## Phase 0 — Project & infrastructure setup
**Goal:** an empty but installable module, Dockerized, in git.

**Build**
- Git repo + `.gitignore` (Python/Odoo), branch strategy (`main` + feature branches per phase).
- `docker-compose.yml`: Odoo 17 + Postgres 15, addons volume mounted to `./`.
- Module skeleton: `nn_fund_management/__manifest__.py`, `__init__.py`, `models/`, `views/`,
  `security/`, `data/`, `tests/`, `static/description/`.
- Manifest: name, version `17.0.1.0.0`, depends `['base', 'mail']` (add `project` later only if you reuse `project.project`).
- Confirm `docker compose up` → module appears in Apps → installs with no error.

**Acceptance:** `nn_fund_management` installs on a clean DB; empty menu root "Fund Management" shows.
**Maps to PDF:** Deliverable #1, #8 (Dockerized), #2 (git).

---

## Phase 1 — Master data & incoming funds (the foundation)
**Goal:** Fund Accounts, Projects, Expense Heads, and recording incoming funds.

**Build**
- `nn.fund.account` (bank/cash/other), `company_id`, currency.
- `nn.expense.head` (Office rent, Salary, Utilities, Marketing, Admin — seed via `data/`).
- Decide projects: **reuse `project.project`** via a related/extension *or* a light `nn.project`.
  Recommendation: light `nn.project` to keep the module self-contained and avoid `project` dep coupling. Document the choice in an ADR.
- `nn.fund.movement` ledger model (immutable lines) — **build it now**, the rest depends on it.
- `nn.incoming.fund`: account, date, amount, txn reference, sender, description, attachment, company, state (`draft→confirmed`).
- On confirm → post an `incoming` ledger line → account *unassigned* rises.
- **Computed account balances** (all `sum` over ledger): total received, available unassigned, on hold, total assigned.
- **Constraints:** unique `(fund_account, transaction_reference)`; amount > 0; no manual balance edit (computed, non-stored-editable).

**Acceptance:** record + confirm BDT 1,000,000 → account unassigned shows 1,000,000; duplicate txn ref in same account is blocked.
**Maps to PDF:** §2, §13 step 1, §14 (computed fields, constraints).

---

## Phase 2 — Reusable approval engine (build once, reuse everywhere)
**Goal:** one abstract approval mixin powering allocations, requisitions, transfers.

**Build**
- `nn.approval.mixin` (`models.AbstractModel`) inheriting `mail.thread`, `mail.activity.mixin`.
- State machine: `draft → submitted → gm_approval → md_approval → approved / rejected / cancelled`.
- `nn.approval.line` (history): approver, date, level, comment, result — appended on every decision.
- Configurable approvers via **security groups**, *not* hardcoded user IDs (PDF §4, §14).
- Server-side guards: GM before MD; only the *current-level* approver acts; cannot approve own request unless flagged; idempotent (each transition posts ledger lines at most once via a `posted` guard).
- Generic `action_submit / action_approve / action_reject / action_cancel` that call model-specific hooks `_on_submit() / _on_approve() / _on_reject()` (where each concrete model posts its own ledger lines).

**Acceptance:** unit test proves MD-before-GM is blocked, self-approval is blocked, and double-clicking Approve posts no duplicate movement.
**Maps to PDF:** §4 (entire), §14 (reusable approval logic), §16.

---

## Phase 3 — Fund Allocation (assign unassigned → project/expense head)
**Goal:** allocation request with hold-on-submit, assign-on-approve, release-on-reject.

**Build**
- `nn.fund.allocation` using the approval mixin: request no. (sequence), account, **project XOR expense head**, amount, purpose, request date, requested-by, attachment, state, approval history.
- `_on_submit`: validate amount ≤ account unassigned → post `hold` lines (money leaves unassigned, sits on hold).
- `_on_approve`: post `assign` lines (hold → assigned under the target project/head).
- `_on_reject`/`_on_cancel`: post `release` lines (back to unassigned).
- **Constraint:** project XOR expense head (exactly one); block if amount > available unassigned.

**Acceptance:** §13 steps 2–5 — request 600k holds it; reject returns it; resubmit+approve assigns it.
**Maps to PDF:** §3 (entire), §13 steps 2–5.

---

## Phase 4 — Project & expense-head balances
**Goal:** the full computed balance picture per project/head, with integrity constraints.

**Build**
- Computed (sum over ledger) on `nn.project` and `nn.expense.head`: total allocated, available,
  requisition hold, transfer hold, approved-but-unspent, total spent, incoming transfers, outgoing transfers.
- **Constraints:** no negative balance anywhere (`@api.constrains`); balance fields are computed/read-only in UI and server-side.
- Smart buttons / stat boxes surfacing these on the form.

**Acceptance:** balances reconcile after Phase-3 actions; attempting any action that would drive a balance negative raises a clear `ValidationError`.
**Maps to PDF:** §5 (entire), §14 (no manual edit, negatives blocked).

---

## Phase 5 — Fund Requisition
**Goal:** request funds *from* a project/head, hold on submit, reserve on approve, remaining-billable tracking.

**Build**
- `nn.fund.requisition` (approval mixin): req no., project/head, requested amount, purpose, request/required dates, requested-by, attachment, state (+`closed`), approval history, **remaining billable amount** (computed).
- `_on_submit`: check available project/head balance → post `hold` (requisition hold).
- `_on_approve`: amount stays reserved for bills (no balance leaves yet; remaining_billable = approved amount).
- reject/cancel → release; **close** when fully billed or unused amount released.

**Acceptance:** §13 step 9 — 150k requisition on Project B holds against its available balance.
**Maps to PDF:** §6 (entire), §13 step 9.

---

## Phase 6 — Bill Control
**Goal:** bills against approved requisitions, partial bills, spend tracking, reversal.

**Build**
- `nn.fund.bill` (custom model — simpler than wiring `account.move` for the assessment; note the choice in ADR).
- Guards: only **approved** requisitions; **same project/head** as the requisition; bill ≤ remaining billable; multiple partials allowed; total billed ≤ approved amount; **Project A cannot use Project B's requisition** (and same-head rule).
- Post → `spend` ledger lines, remaining billable decreases.
- Cancel/reverse → compensating `reverse` line returns to remaining billable; **must not create funds**.

**Acceptance:** §13 steps 10–13 — 100k partial bill leaves 50k billable; a 60k bill is blocked; cross-project use is blocked.
**Maps to PDF:** §7 (entire), §13 steps 10–13.

---

## Phase 7 — Fund Transfer
**Goal:** move funds between projects/heads with hold-on-submit, move-on-approve.

**Build**
- `nn.fund.transfer` (approval mixin): transfer no., source, destination (any project/head combo), amount, reason, requested-by, date, state, history.
- `_on_submit`: amount ≤ source available → post `transfer_out` hold on source.
- `_on_approve`: post `transfer_in` to destination (hold cleared, destination balance rises).
- reject/cancel → release to source.
- **Constraints:** source ≠ destination; amount ≤ source available; held transfer funds unusable elsewhere.

**Acceptance:** §13 steps 6–8 — 200k transfer A→B holds while pending, lands on approve; held funds can't be re-used.
**Maps to PDF:** §8 (entire), §13 steps 6–8, §16.

---

## Phase 8 — Security & access control (MUST — server-side, not just UI)
**Goal:** real, server-enforced permissions.

**Build**
- Groups: Fund User, Finance User, GM Approver, MD Approver, Fund Administrator (`security/groups.xml`).
- `ir.model.access.csv` for every model (CRUD per group).
- **Record rules:** multi-company isolation; users see only allowed requests; only finance confirms incoming funds; only authorized users cancel approved transactions.
- Server-side checks in approve/cancel methods (don't rely on hiding buttons).

**Acceptance:** a Fund User cannot approve; a non-finance user cannot confirm incoming funds; cross-company records are invisible — all enforced server-side (prove with a test using `with_user`).
**Maps to PDF:** §9 (entire — "hiding buttons is not enough"), §14, §16.

---

## Phase 9 — Audit history
**Goal:** a clear, preserved trail of every financial action.

**Build**
- `mail.thread` tracking on key fields (amount, state) across all transaction models.
- History captures: creator, submitter, approver/rejecter, prev→new status, datetime, comment, amount, related account, related project/head, reference doc (the ledger + chatter + approval lines together cover this).
- Block deletion of confirmed financial records (override `unlink` → require cancel/reverse first).

**Acceptance:** every record's chatter + ledger shows full who/when/what; deleting a confirmed record is refused.
**Maps to PDF:** §10 (entire).

---

## Phase 10 — Automated tests (MUST — they grade test quality)
**Goal:** tests that prove the integrity rules, mirroring the Sample Demonstration.

**Build (`tests/`, `TransactionCase`)**
- Balance math (incoming → unassigned, allocation hold/assign/release).
- **Double-spend:** held funds can't be allocated/requisitioned/transferred again; idempotent approval.
- Approval order (MD-before-GM blocked), self-approval blocked, security via `with_user`.
- Bill rules: partial bills, over-bill blocked, cross-project blocked, reversal restores billable without creating funds.
- **One end-to-end test replicating §13 steps 1–13.**

**Acceptance:** `odoo -i nn_fund_management --test-enable` (or `--test-tags`) runs green; the §13 scenario passes as one test.
**Maps to PDF:** §14, §15 (automated test quality), §16 (add a new test live).

---

## Phase 11 — Bonus features (only after MUST + SHOULD are solid)
**Goal:** extra credit. Pick in this order; each is independent.

1. **Configurable approval rules** — `nn.approval.rule` keyed on request type / amount band / company / category / sequence / group (e.g. ≤50k GM; 50k–200k GM+Finance; >200k GM+Finance+MD). The approval engine reads rules instead of a fixed GM→MD chain.
2. **Bank email integration** — `fetchmail`/`mail.thread` inbound parsing → `nn.incoming.fund` in "Pending Verification"; identify bank/account/ref/date/amount/sender/message-id; dedupe by message-id + txn ref; log parse failures; **no real credentials in source**.
3. **Dashboard & notifications** — OWL/QWeb dashboard (received, unassigned, held, assigned, spent, pending approvals, project/head balances, recent movements) + `mail.activity` on submit/approve/reject/near-full requisition/email-failure.

**Maps to PDF:** §11 (entire), §10/§13 dashboard items.

---

## Phase 12 — Delivery (always reserve the final day)
**Goal:** ship every required artifact.

**Build**
- `README.md`: Odoo version, install steps, dependencies, configuration, **testing instructions**, assumptions, known limitations.
- `docs/01-architecture/architecture.md` finalized (the "short architecture explanation" deliverable).
- `docs/05-ai-usage/ai-usage-log.md`: AI tools, AI-assisted parts, key prompts, errors found in AI output, your changes, what you fully understood — **this is your video script**.
- Clean, meaningful git history (you've been committing per phase).
- Screen recording **with facecam**, kept short, Google Drive **public** link.
- Optional: live server deploy.

**Maps to PDF:** Deliverables #3, #5, #6, #7; video-explanation bullets; §15.

---

## Definition of Done (every phase)
- [ ] Module installs/upgrades on a clean DB with no traceback.
- [ ] New balance logic is expressed as **ledger lines**, never a manual balance write.
- [ ] Server-side constraints + clear `ValidationError` messages (not just UI hiding).
- [ ] No hardcoded user/DB IDs; sequences/refs use `ir.sequence`.
- [ ] At least the phase's acceptance scenario is covered by a test (from Phase 10 onward, formalized).
- [ ] Committed on a feature branch with a meaningful message; `backlog.md` ticket ticked.
- [ ] If a design choice was made (e.g. custom bill vs `account.move`), an ADR line is added.
