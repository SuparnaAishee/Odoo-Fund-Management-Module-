# -*- coding: utf-8 -*-
from odoo import fields, models


class NnProject(models.Model):
    """Light, self-contained project model (ADR-0002) -- intentionally not
    coupled to the heavy ``project`` app. A fund bucket that can hold balances.
    The full computed balance picture is added in Phase 4."""

    _name = "nn.project"
    _description = "Fund Project"
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

    movement_ids = fields.One2many("nn.fund.movement", "project_id", string="Movements")
