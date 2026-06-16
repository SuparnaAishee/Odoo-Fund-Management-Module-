# -*- coding: utf-8 -*-
from odoo import fields, models


class ExpenseHead(models.Model):
    """An expense head is the second kind of fund bucket (Office rent, Salary,
    Utilities, ...). Like ``nn.project`` it holds balances computed from the
    ledger; the full picture is added in Phase 4."""

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
