# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

PENDING_STATES = ("submitted", "gm_approval", "md_approval")


class FundDashboard(models.Model):
    """A single-record overview of fund balances and pending work. Every figure
    is read live from the accounts, buckets and approval requests, so the
    dashboard never stores a balance of its own."""

    _name = "nn.fund.dashboard"
    _description = "Fund Management Dashboard"

    name = fields.Char(default="Fund Overview", readonly=True)
    currency_id = fields.Many2one(
        "res.currency", readonly=True,
        default=lambda self: self.env.company.currency_id,
    )

    total_received = fields.Monetary(compute="_compute_kpis")
    total_unassigned = fields.Monetary(compute="_compute_kpis")
    total_on_hold = fields.Monetary(compute="_compute_kpis")
    total_assigned = fields.Monetary(compute="_compute_kpis")
    total_spent = fields.Monetary(compute="_compute_kpis")
    pending_approvals = fields.Integer(compute="_compute_kpis")

    project_count = fields.Integer(compute="_compute_kpis")
    expense_head_count = fields.Integer(compute="_compute_kpis")
    movement_count = fields.Integer(compute="_compute_kpis")

    project_ids = fields.Many2many("nn.project", compute="_compute_lists")
    expense_head_ids = fields.Many2many("nn.expense.head", compute="_compute_lists")
    recent_movement_ids = fields.Many2many("nn.fund.movement", compute="_compute_lists")

    @api.depends("name")
    def _compute_lists(self):
        projects = self.env["nn.project"].search([])
        heads = self.env["nn.expense.head"].search([])
        movements = self.env["nn.fund.movement"].search([], limit=12)
        for rec in self:
            rec.project_ids = projects
            rec.expense_head_ids = heads
            rec.recent_movement_ids = movements

    @api.depends("name")
    def _compute_kpis(self):
        accounts = self.env["nn.fund.account"].search([])
        projects = self.env["nn.project"].search([])
        heads = self.env["nn.expense.head"].search([])
        pending = (
            self.env["nn.fund.allocation"].search_count([("state", "in", PENDING_STATES)])
            + self.env["nn.fund.requisition"].search_count([("state", "in", PENDING_STATES)])
            + self.env["nn.fund.transfer"].search_count([("state", "in", PENDING_STATES)])
        )
        for rec in self:
            rec.total_received = sum(accounts.mapped("received"))
            rec.total_unassigned = sum(accounts.mapped("unassigned"))
            rec.total_on_hold = sum(accounts.mapped("on_hold"))
            rec.total_assigned = sum(accounts.mapped("assigned"))
            rec.total_spent = sum(projects.mapped("spent")) + sum(heads.mapped("spent"))
            rec.pending_approvals = pending
            rec.project_count = len(projects)
            rec.expense_head_count = len(heads)
            rec.movement_count = self.env["nn.fund.movement"].search_count([])

    def action_open_recent_movements(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Recent Fund Movements"),
            "res_model": "nn.fund.movement",
            "view_mode": "tree",
            "target": "current",
        }
