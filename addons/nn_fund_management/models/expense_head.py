# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from .bucket_balance import bucket_sums


class ExpenseHead(models.Model):
    """An expense head is the second kind of fund bucket (Office rent, Salary,
    Utilities, ...). It shares the exact same ledger-derived balance logic as
    ``nn.project`` (see ``bucket_balance``), so the two can never drift."""

    _name = "nn.expense.head"
    _description = "Expense Head"
    _order = "name"

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code")
    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency", string="Currency", required=True,
        default=lambda self: self.env.company.currency_id,
    )
    active = fields.Boolean(default=True)

    movement_ids = fields.One2many("nn.fund.movement", "expense_head_id", string="Movements")
    movement_count = fields.Integer(compute="_compute_movement_count")

    allocated = fields.Monetary(string="Allocated", compute="_compute_balances", store=True)
    available = fields.Monetary(string="Available", compute="_compute_balances", store=True)
    requisition_hold = fields.Monetary(string="Requisition Hold", compute="_compute_balances", store=True)
    transfer_hold = fields.Monetary(string="Transfer Hold", compute="_compute_balances", store=True)
    spent = fields.Monetary(string="Spent", compute="_compute_balances", store=True)
    transfer_in = fields.Monetary(string="Transfers In", compute="_compute_balances", store=True)
    transfer_out = fields.Monetary(string="Transfers Out", compute="_compute_balances", store=True)

    @api.depends("movement_ids.move_type", "movement_ids.amount")
    def _compute_balances(self):
        for rec in self:
            vals = bucket_sums(rec.movement_ids)
            rec.update(vals)

    def _compute_movement_count(self):
        for rec in self:
            rec.movement_count = len(rec.movement_ids)

    @api.constrains("movement_ids")
    def _check_non_negative(self):
        # BR-04: no bucket balance may go negative.
        for rec in self:
            cur = rec.currency_id
            for label, value in (
                ("available", rec.available),
                ("requisition hold", rec.requisition_hold),
                ("transfer hold", rec.transfer_hold),
                ("spent", rec.spent),
            ):
                if cur.compare_amounts(value, 0.0) < 0:
                    raise ValidationError(_(
                        "Expense head %(name)s would have a negative %(label)s balance.",
                        name=rec.name, label=label,
                    ))

    def action_view_movements(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Movements"),
            "res_model": "nn.fund.movement",
            "view_mode": "tree",
            "domain": [("expense_head_id", "=", self.id)],
        }
