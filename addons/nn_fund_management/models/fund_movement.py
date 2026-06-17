# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

# Append-only ledger: every money event is one immutable row, and all balances
# elsewhere are computed sums over these rows. Move types are explicit so each
# balance is an unambiguous sum over a single type, with no per-model branching:
#
#   incoming                              account: +received, +unassigned
#   alloc_hold / alloc_release / assign   account: unassigned <-> on_hold -> assigned
#   req_hold / req_release / spend / reverse      bucket: available <-> hold <-> spent
#   transfer_hold / transfer_release / transfer_settle    bucket: source side
#   transfer_in                                           bucket: destination side
MOVE_TYPES = [
    ("incoming", "Incoming"),
    ("alloc_hold", "Allocation Hold"),
    ("alloc_release", "Allocation Release"),
    ("assign", "Assign"),
    ("req_hold", "Requisition Hold"),
    ("req_release", "Requisition Release"),
    ("spend", "Spend"),
    ("reverse", "Reverse"),
    ("transfer_hold", "Transfer Hold"),
    ("transfer_release", "Transfer Release"),
    ("transfer_settle", "Transfer Settle"),
    ("transfer_in", "Transfer In"),
]


class FundMovement(models.Model):
    _name = "nn.fund.movement"
    _description = "Fund Movement (immutable ledger line)"
    _order = "date desc, id desc"
    _rec_name = "display_name"

    date = fields.Datetime(
        string="Date", required=True, default=fields.Datetime.now, index=True
    )
    move_type = fields.Selection(
        MOVE_TYPES, string="Type", required=True, index=True
    )
    amount = fields.Monetary(string="Amount", required=True)
    currency_id = fields.Many2one(
        "res.currency", string="Currency", required=True,
        default=lambda self: self.env.company.currency_id,
    )
    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda self: self.env.company,
    )

    account_id = fields.Many2one("nn.fund.account", string="Account", index=True, ondelete="restrict")
    project_id = fields.Many2one("nn.project", string="Project", index=True, ondelete="restrict")
    expense_head_id = fields.Many2one("nn.expense.head", string="Expense Head", index=True, ondelete="restrict")

    # Source document as model/id, so the ledger never hard-depends on a model.
    origin_model = fields.Char(string="Source Model", index=True)
    origin_id = fields.Integer(string="Source ID", index=True)
    reference = fields.Char(string="Reference")
    state = fields.Char(string="Source State", help="Mirrors the source document state for filtering.")

    display_name = fields.Char(compute="_compute_display_name")

    _sql_constraints = [
        ("amount_positive", "CHECK(amount > 0)", "A fund movement amount must be strictly positive."),
    ]

    @api.model
    def _post(self, move_type, amount, origin, account=False, project=False, expense_head=False):
        """Single entry point for posting a ledger line. Runs as superuser since
        the ledger is read-only to everyone; the caller has already done its own
        access checks."""
        company = origin.company_id if origin.company_id else self.env.company
        currency = origin.currency_id if origin.currency_id else company.currency_id
        return self.sudo().create({
            "move_type": move_type,
            "amount": amount,
            "account_id": account.id if account else False,
            "project_id": project.id if project else False,
            "expense_head_id": expense_head.id if expense_head else False,
            "currency_id": currency.id,
            "company_id": company.id,
            "origin_model": origin._name,
            "origin_id": origin.id,
            "reference": origin.display_name,
            "state": origin.state if "state" in origin._fields else False,
        })

    @api.depends("move_type", "amount", "reference")
    def _compute_display_name(self):
        type_label = dict(MOVE_TYPES)
        for move in self:
            label = type_label.get(move.move_type, move.move_type or "")
            move.display_name = "%s: %s" % (label, move.reference or move.amount)

    # The ledger is append-only: edits and deletes are blocked, post a reversal.
    def write(self, vals):
        raise UserError(_(
            "Fund movements are immutable. Post a compensating reversal instead "
            "of editing the ledger."
        ))

    def unlink(self):
        raise UserError(_(
            "Fund movements are immutable and cannot be deleted. Post a "
            "compensating reversal instead."
        ))
