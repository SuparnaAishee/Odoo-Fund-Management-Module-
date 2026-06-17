# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FundAccount(models.Model):
    _name = "nn.fund.account"
    _description = "Fund Account (bank / cash)"
    _order = "name"

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code")
    account_type = fields.Selection(
        [("bank", "Bank"), ("cash", "Cash"), ("other", "Other")],
        string="Type", required=True, default="bank",
    )
    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency", string="Currency", required=True,
        default=lambda self: self.env.company.currency_id,
    )
    active = fields.Boolean(default=True)

    movement_ids = fields.One2many("nn.fund.movement", "account_id", string="Movements")

    # All balances are computed sums over the ledger, never written by hand.
    received = fields.Monetary(string="Total Received", compute="_compute_balances", store=True)
    unassigned = fields.Monetary(string="Available (Unassigned)", compute="_compute_balances", store=True)
    on_hold = fields.Monetary(string="On Hold", compute="_compute_balances", store=True)
    assigned = fields.Monetary(string="Assigned", compute="_compute_balances", store=True)

    @api.depends("movement_ids.move_type", "movement_ids.amount")
    def _compute_balances(self):
        for account in self:
            sums = dict.fromkeys(
                ("incoming", "alloc_hold", "alloc_release", "assign"), 0.0
            )
            for move in account.movement_ids:
                if move.move_type in sums:
                    sums[move.move_type] += move.amount
            account.received = sums["incoming"]
            account.unassigned = sums["incoming"] - sums["alloc_hold"] + sums["alloc_release"]
            account.on_hold = sums["alloc_hold"] - sums["alloc_release"] - sums["assign"]
            account.assigned = sums["assign"]

    @api.constrains("movement_ids")
    def _check_non_negative(self):
        # An account's unassigned and on-hold balances can never go negative.
        for account in self:
            if account.currency_id.compare_amounts(account.unassigned, 0.0) < 0:
                raise ValidationError(_(
                    "Account %s would have a negative unassigned balance.", account.name
                ))
            if account.currency_id.compare_amounts(account.on_hold, 0.0) < 0:
                raise ValidationError(_(
                    "Account %s would have a negative on-hold balance.", account.name
                ))
