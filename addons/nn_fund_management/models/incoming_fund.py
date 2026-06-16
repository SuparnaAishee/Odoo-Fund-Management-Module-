# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class IncomingFund(models.Model):
    _name = "nn.incoming.fund"
    _description = "Incoming Fund"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(string="Reference", required=True, copy=False, readonly=True, default=lambda self: _("New"))
    fund_account_id = fields.Many2one(
        "nn.fund.account", string="Fund Account", required=True, tracking=True,
    )
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today, tracking=True)
    amount = fields.Monetary(string="Amount", required=True, tracking=True)
    currency_id = fields.Many2one(related="fund_account_id.currency_id", store=True, readonly=True)
    company_id = fields.Many2one(related="fund_account_id.company_id", store=True, readonly=True)

    transaction_reference = fields.Char(string="Transaction Reference", required=True, tracking=True)
    sender = fields.Char(string="Sender")
    description = fields.Text(string="Description")
    attachment_ids = fields.Many2many("ir.attachment", string="Attachments")

    state = fields.Selection(
        [("draft", "Draft"), ("confirmed", "Confirmed")],
        string="Status", default="draft", required=True, tracking=True,
    )
    movement_id = fields.Many2one("nn.fund.movement", string="Ledger Movement", readonly=True, copy=False)

    _sql_constraints = [
        ("amount_positive", "CHECK(amount > 0)", "The incoming amount must be greater than zero."),
        ("unique_account_txn_ref",
         "UNIQUE(fund_account_id, transaction_reference)",
         "This transaction reference already exists for this fund account."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("nn.incoming.fund") or _("New")
        return super().create(vals_list)

    def action_confirm(self):
        """Confirm a deposit -> post one immutable ``incoming`` ledger line so
        the amount enters the account's unassigned balance (BR-07)."""
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only draft incoming funds can be confirmed."))
            movement = self.env["nn.fund.movement"].sudo().create({
                "move_type": "incoming",
                "amount": record.amount,
                "account_id": record.fund_account_id.id,
                "currency_id": record.currency_id.id,
                "company_id": record.company_id.id,
                "origin_model": record._name,
                "origin_id": record.id,
                "reference": record.name,
                "state": "confirmed",
            })
            record.write({"state": "confirmed", "movement_id": movement.id})
        return True

    def action_draft(self):
        # Reverting to draft is not allowed once posted (BR-01/BR-40): an
        # incoming line cannot be un-posted, only compensated.
        raise UserError(_(
            "A confirmed incoming fund cannot be reset to draft; it has already "
            "posted to the ledger."
        ))
