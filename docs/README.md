
# nn_fund_management — Documentation Index

Documentation set for the **NN Services Odoo Fund Management** technical assessment.
Right-sized for a single Odoo module (not a full product), but structured the way a
real engineering team would maintain an R&D module: business → architecture →
technical spec → development → quality → AI transparency.

> Read order for a reviewer: `00 → 01 → 02`. Read order for *building it*: `03-development/development-plan.md` (do the phases one by one).

## Folder map

| Folder | Purpose | Key documents |
|--------|---------|---------------|
| `00-product/` | What & why — the business problem, rules, glossary | `brd.md`, `business-rules.md`, `glossary.md` |
| `01-architecture/` | High-level design, the **ledger** decision, diagrams | `architecture.md`, `erd.md`, `state-machines.md`, `adr/` |
| `02-technical-spec/` | Per-model field specs, computed formulas, constraints, security matrix | `models-spec.md`, `security-matrix.md` |
| `03-development/` | **The phased build plan** + backlog | `development-plan.md` ⭐, `backlog.md` |
| `04-quality/` | Test plan + traceability to the rubric | `test-plan.md`, `traceability-matrix.md` |
| `05-ai-usage/` | AI-transparency log for the required video | `ai-usage-log.md` |

Plus, at repo root (deliverables required by the PDF):
`README.md` (install/run), `CLAUDE.md` (AI context), `docker-compose.yml`, the addon folder `nn_fund_management/`.

## The one architectural decision that matters most: the Fund Movement Ledger

The assessment is graded on **"the same money cannot be allocated, transferred or spent
more than once"** and **"balance fields calculated automatically, never manually edited."**

The robust, audit-friendly, scalable way to satisfy both is an **append-only ledger**:

- A single model `nn.fund.movement` records every atomic money event as an immutable line:
  `(date, source_ref, amount, type, from_bucket, to_bucket, state, origin_document)`.
- Movement types: `incoming`, `hold`, `release`, `assign`, `spend`, `transfer_in`, `transfer_out`, `reverse`.
- **All balance fields are computed `sum()` over ledger lines** — never stored-and-mutated by hand.
  - Account *unassigned* = Σ incoming − Σ (held + assigned) for that account.
  - Project *available* = Σ assigned-in + transfers-in − holds − spend − transfers-out.
- Every workflow action (submit/approve/reject/cancel/bill/reverse) **posts ledger lines**;
  it never edits a balance directly.
- **Double-spend prevention** = idempotent posting: each action posts at most once, guarded by
  state + a `posted` flag, so "repeated approval actions do not create duplicate fund movements" (PDF §4).

Benefits: every balance is explainable by drilling into its lines (this *is* the audit history §10),
reversals are just compensating lines (no funds created), and `@api.constrains` can forbid any
ledger state that would drive a balance negative.

> This pattern is the spine of the whole module. Phases 1–7 of the development plan all
> express their logic as "post these ledger lines," which keeps the codebase small and consistent.

## Evaluation of the reference formats (the two screenshots)

- **Keep:** layered docs (business/architecture/technical/functional), `CLAUDE.md` as AI context,
  Epic→Story→Task with technical acceptance criteria.
- **Drop for this scope:** product-concept-note / pptx / multi-doc product specs — that set is sized
  for a full product, not one module. It would burn time better spent on tests and the video.
- **Add (not in the references):** the Ledger design doc above, ERD + state-machine diagrams,
  and a rubric traceability matrix. These three target exactly what NN says they grade.
