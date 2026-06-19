# -*- coding: utf-8 -*-
"""Shared balance math for fund buckets (projects and expense heads).

A bucket is any target that can hold allocated funds. Its balances are pure sums
over the ledger lines referencing it, so one function serves both ``nn.project``
and ``nn.expense.head`` and they can never drift apart. The amounts conserve:

    allocated + transfer_in
        == available + requisition_hold + transfer_hold + spent + transfer_out
"""

_BUCKET_MOVE_TYPES = (
    "assign", "assign_reverse", "transfer_in", "transfer_in_reverse",
    "transfer_settle", "transfer_settle_reverse",
    "req_hold", "req_release", "spend", "reverse",
    "transfer_hold", "transfer_release",
)


def bucket_sums(movements):
    """Return the computed balance dict for a set of ledger ``movements`` that
    all reference one bucket."""
    s = dict.fromkeys(_BUCKET_MOVE_TYPES, 0.0)
    for move in movements:
        if move.move_type in s:
            s[move.move_type] += move.amount

    # The *_reverse lines compensate an approved transaction that an authorised
    # user later cancelled, so they net straight off their originals.
    allocated = s["assign"] - s["assign_reverse"]
    transfer_in = s["transfer_in"] - s["transfer_in_reverse"]
    transfer_out = s["transfer_settle"] - s["transfer_settle_reverse"]
    # Held from submit; spending converts the hold into spent.
    requisition_hold = s["req_hold"] - s["req_release"] - s["spend"] + s["reverse"]
    transfer_hold = s["transfer_hold"] - s["transfer_release"] - s["transfer_settle"]
    spent = s["spend"] - s["reverse"]
    available = (
        allocated + transfer_in - transfer_out
        - requisition_hold - transfer_hold - spent
    )
    return {
        "allocated": allocated,
        "available": available,
        "requisition_hold": requisition_hold,
        "transfer_hold": transfer_hold,
        "spent": spent,
        "transfer_in": transfer_in,
        "transfer_out": transfer_out,
    }
