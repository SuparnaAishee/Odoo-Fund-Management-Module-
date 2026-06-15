# ADR-0003: Custom `nn.fund.bill` instead of `account.move`

**Status:** Accepted · **Date:** 2026-06-15

## Context
PDF §7 allows either integrating bills with Odoo Vendor Bills (`account.move`) or creating a
custom bill model. Bills must link to an approved requisition, support partial billing, enforce
same-bucket and remaining-billable rules, and reverse without creating funds.

## Decision
Implement a custom `nn.fund.bill` model.

## Rationale
- **Focused rule enforcement:** all the §7 constraints (approved-req only, same project/head,
  ≤ remaining billable, total ≤ approved, cross-project block) live cleanly on one small model.
- **No accounting setup burden:** `account.move` requires journals, accounts, taxes, fiscal
  config — irrelevant to fund tracking and a setup/grading liability under deadline.
- **Ledger consistency:** a bill simply posts `spend` / `reverse` movements, identical in shape
  to the rest of the module.

## Consequences
- No GL/journal entries, no vendor-payment lifecycle (out of scope per BRD §4).
- A future bridge to `account.move` can mirror posted bills if real accounting is needed later.

## Alternatives rejected
- **`account.move` (Vendor Bills):** powerful but heavy; the assessment explicitly permits a
  custom model, and the integrity rules are clearer on a dedicated entity.
