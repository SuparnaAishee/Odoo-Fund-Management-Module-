# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class FundBill(models.Model):
    """A bill spends against an approved requisition. Partial bills are allowed;
    posting marks the amount spent, reversing returns it to remaining-billable
    and creates no funds."""

    _name = "nn.fund.bill"
    _description = "Fund Bill"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(string="Reference", required=True, copy=False, readonly=True, default=lambda self: _("New"))
    requisition_id = fields.Many2one(
        "nn.fund.requisition", string="Requisition", required=True, tracking=True,
        domain="[('state', '=', 'approved')]",
    )
    amount = fields.Monetary(string="Amount", required=True, tracking=True)
    date = fields.Date(string="Bill Date", required=True, default=fields.Date.context_today)
    description = fields.Text(string="Description")

    # Bucket and currency follow the requisition, so a bill can never land on
    # another bucket.
    project_id = fields.Many2one(related="requisition_id.project_id", store=True, readonly=True)
    expense_head_id = fields.Many2one(related="requisition_id.expense_head_id", store=True, readonly=True)
    currency_id = fields.Many2one(related="requisition_id.currency_id", store=True, readonly=True)
    company_id = fields.Many2one(related="requisition_id.company_id", store=True, readonly=True)
    remaining_billable = fields.Monetary(related="requisition_id.remaining_billable", readonly=True)

    state = fields.Selection(
        [("draft", "Draft"), ("posted", "Posted"), ("cancelled", "Cancelled")],
        string="Status", default="draft", required=True, tracking=True, copy=False,
    )

    _sql_constraints = [
        ("amount_positive", "CHECK(amount > 0)", "The bill amount must be greater than zero."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("nn.fund.bill") or _("New")
        return super().create(vals_list)

    def action_post(self):
        self = self.with_context(mail_notify_force_send=False)
        Move = self.env["nn.fund.movement"]
        for bill in self:
            if bill.state != "draft":
                raise UserError(_("Only a draft bill can be posted."))
            req = bill.requisition_id
            if req.state != "approved":
                raise ValidationError(_(
                    "A bill can only be posted against an approved requisition."
                ))
            if bill.currency_id.compare_amounts(bill.amount, req.remaining_billable) > 0:
                raise ValidationError(_(
                    "Bill of %(amount)s exceeds the requisition's remaining "
                    "billable amount of %(remaining)s.",
                    amount=bill.amount, remaining=req.remaining_billable,
                ))
            Move._post(
                "spend", bill.amount, bill,
                project=req.project_id, expense_head=req.expense_head_id,
            )
            bill.state = "posted"
            # Alert when a requisition is almost fully billed (<= 10% left).
            remaining = req.remaining_billable
            if remaining > 0 and bill.currency_id.compare_amounts(remaining, req.amount * 0.1) <= 0:
                req.message_post(body=_(
                    "Requisition %(name)s is almost fully billed — %(left)s remaining.",
                    name=req.name, left=remaining,
                ))
        return True

    def action_reverse(self):
        """Reverse a posted bill: a compensating line returns the amount to
        remaining-billable and creates no new funds."""
        self = self.with_context(mail_notify_force_send=False)
        Move = self.env["nn.fund.movement"]
        for bill in self:
            if bill.state != "posted":
                raise UserError(_("Only a posted bill can be reversed."))
            req = bill.requisition_id
            Move._post(
                "reverse", bill.amount, bill,
                project=req.project_id, expense_head=req.expense_head_id,
            )
            bill.state = "cancelled"
        return True

    def action_cancel(self):
        for bill in self:
            if bill.state != "draft":
                raise UserError(_("Only a draft bill can be cancelled; post a reversal instead."))
            bill.state = "cancelled"
        return True
