# AI Usage Log (and video script)

This file satisfies the PDF's AI-transparency requirement and doubles as the outline for the
required screen recording (facecam, short, Google Drive public link). **Fill it in as you build** —
don't reconstruct it at the end.

## AI tools used
| Tool | Used for |
|------|----------|
| _e.g._ Claude Code | scaffolding, ledger design discussion, test drafting |
| _(add others)_ | _(IDE assistant, ChatGPT, etc.)_ |

## Per-phase log (append a row each time you use AI)
| Date | Phase | What AI produced | What I changed / fixed | Did I fully understand it? |
|------|-------|------------------|------------------------|----------------------------|
| | 0 | | | |
| | 1 | | | |
| | ... | | | |

## Important prompts (summaries)
- _"Design a double-spend-proof balance model for an Odoo fund module"_ → led to the ledger (ADR-0001).
- _(record the 4–6 prompts that actually shaped the code)_

## Errors found in AI-generated code
> Capturing real bugs you caught is strong evidence you understand the code. Examples to watch for:
- Computed balance fields without correct `@api.depends` → stale balances.
- Approval action not guarded → double-posting on re-click (had to add `posted` guard).
- Missing `XOR` constraint allowing both project and head set.
- Record rule using a hardcoded user/company id.
- _(log the actual ones you hit)_

## What I changed vs. accepted as-is
- _(list the parts you rewrote, refactored, or rejected)_

## Parts fully understood & implemented by me
- _(be honest and specific — e.g. "wrote the ledger posting + conservation logic and all tests myself")_

## Known limitations
- _(carry over from README known-limitations; e.g. bonus features partial, custom bill not GL-integrated)_

---

## Video running order (keep it short)
1. 30s: what the module does + the ledger idea (one sentence: "every balance is a sum of immutable movements").
2. UI demo = the §13 scenario (receive → allocate → reject → re-approve → transfer → requisition → partial bill → blocked bill → cross-project block).
3. Code tour: nn.approval.mixin (reusable), one posting method, one `@api.constrains`, the ACL/record rule.
4. Run the tests live (green).
5. AI transparency: tools, key prompts, an error you caught, what you wrote yourself, limitations.
