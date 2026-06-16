# -*- coding: utf-8 -*-
"""Shared balance math for fund buckets (projects and expense heads).

A *bucket* is any target that can hold allocated funds. All of its balances are
pure sums over the ledger lines that reference it, so the same function serves
both ``nn.project`` and ``nn.expense.head`` and the two can never drift apart.

Money conservation for a bucket (proved by construction):
    allocated + transfer_in
        == available + requisition_hold + transfer_hold + spent + transfer_out
"""

_BUCKET_MOVE_TYPES = (
    "assign", "transfer_in", "transfer_settle",
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

    allocated = s["assign"]
    transfer_in = s["transfer_in"]
    transfer_out = s["transfer_settle"]
    # A reservation is held from submit; spending it converts hold -> spent.
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
