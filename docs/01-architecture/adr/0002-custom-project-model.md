# ADR-0002: Light custom `nn.project` instead of reusing `project.project`

**Status:** Accepted · **Date:** 2026-06-15

## Context
Funds may be assigned to "a project". Odoo ships a `project` app with `project.project`. We must
decide whether to reuse it or model a light custom entity.

## Decision
Use a custom `nn.project` model (name, code, company, computed balance fields), **not**
`project.project`.

## Rationale
- **No dependency coupling:** avoids depending on the `project` app and its data model churn
  across Odoo versions; the module stays self-contained and easy to install/grade.
- **Clean balance ownership:** the many computed balance fields (allocated/available/holds/
  spent/transfers) belong naturally on our own model rather than bolted onto `project.project`.
- **Symmetry with `nn.expense.head`:** projects and expense heads behave as interchangeable
  "buckets"; giving them parallel custom models keeps allocation/transfer/requisition logic uniform.
- **Demo simplicity:** the §13 scenario only needs Project A / Project B with balances.

## Consequences
- No native Gantt/task integration (out of scope — see BRD §4).
- If real `project.project` integration is later required, add an optional bridge module; the
  ledger design makes that additive, not a rewrite.

## Alternatives rejected
- **Reuse `project.project`:** heavier dependency, awkward balance extension, more version risk —
  not worth it for an assessment whose project needs are minimal.
