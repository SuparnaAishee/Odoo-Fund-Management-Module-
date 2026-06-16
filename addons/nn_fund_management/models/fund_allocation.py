# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FundAllocation(models.Model):
    """Assign unassigned account funds to a project XOR an expense head, through
    the GM -> MD approval chain. Hold on submit, assign on approve, release on
    reject/cancel (PDF section 3)."""

    _name = "nn.fund.allocation"
    _description = "Fund Allocation"
    _inherit = ["nn.approval.mixin"]
    _order = "request_date desc, id desc"

    name = fields.Char(string="Reference", required=True, copy=False, readonly=True, default=lambda self: _("New"))
    fund_account_id = fields.Many2one("nn.fund.account", string="Fund Account", required=True, tracking=True)
    project_id = fields.Many2one("nn.project", string="Project", tracking=True)
    expense_head_id = fields.Many2one("nn.expense.head", string="Expense Head", tracking=True)
    amount = fields.Monetary(string="Amount", required=True, tracking=True)
    currency_id = fields.Many2one(related="fund_account_id.currency_id", store=True, readonly=True)
    company_id = fields.Many2one(related="fund_account_id.company_id", store=True, readonly=True)

    purpose = fields.Text(string="Purpose")
    request_date = fields.Date(string="Request Date", required=True, default=fields.Date.context_today)
    attachment_ids = fields.Many2many("ir.attachment", string="Attachments")

    # Convenience: the chosen target bucket, for display.
    target_name = fields.Char(string="Target", compute="_compute_target_name")

    _sql_constraints = [
        ("amount_positive", "CHECK(amount > 0)", "The allocation amount must be greater than zero."),
    ]

    @api.depends("project_id", "expense_head_id")
    def _compute_target_name(self):
        for rec in self:
            rec.target_name = rec.project_id.display_name or rec.expense_head_id.display_name or ""

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("nn.fund.allocation") or _("New")
        return super().create(vals_list)

    # -- BR-09: a request targets a project XOR an expense head ------------ #
    @api.constrains("project_id", "expense_head_id")
    def _check_single_target(self):
        for rec in self:
            if bool(rec.project_id) == bool(rec.expense_head_id):
                raise ValidationError(_(
                    "An allocation must target exactly one of a project or an "
                    "expense head (never both, never neither)."
                ))

    # -- Approval-mixin hooks ---------------------------------------------- #
    def _validate_submit(self):
        # BR-10: cannot hold more than the account currently has unassigned.
        for rec in self:
            available = rec.fund_account_id.unassigned
            if rec.currency_id.compare_amounts(rec.amount, available) > 0:
                raise ValidationError(_(
                    "Allocation of %(amount)s exceeds the account's unassigned "
                    "balance of %(available)s.",
                    amount=rec.amount, available=available,
                ))
        return True

    def _post_on_submit(self):
        Move = self.env["nn.fund.movement"]
        for rec in self:
            Move._post("alloc_hold", rec.amount, rec, account=rec.fund_account_id)
        return True

    def _post_on_approve(self):
        Move = self.env["nn.fund.movement"]
        for rec in self:
            Move._post(
                "assign", rec.amount, rec,
                account=rec.fund_account_id,
                project=rec.project_id, expense_head=rec.expense_head_id,
            )
        return True

    def _post_on_reject(self):
        Move = self.env["nn.fund.movement"]
        for rec in self:
            Move._post("alloc_release", rec.amount, rec, account=rec.fund_account_id)
        return True
