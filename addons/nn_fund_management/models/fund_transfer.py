# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FundTransfer(models.Model):
    """Move funds between two buckets. Hold the source on submit, settle out of
    the source and into the destination on approve, release on reject/cancel."""

    _name = "nn.fund.transfer"
    _description = "Fund Transfer"
    _inherit = ["nn.approval.mixin"]
    _order = "request_date desc, id desc"

    name = fields.Char(string="Reference", required=True, copy=False, readonly=True, default=lambda self: _("New"))

    src_project_id = fields.Many2one("nn.project", string="Source Project", tracking=True)
    src_head_id = fields.Many2one("nn.expense.head", string="Source Head", tracking=True)
    dest_project_id = fields.Many2one("nn.project", string="Destination Project", tracking=True)
    dest_head_id = fields.Many2one("nn.expense.head", string="Destination Head", tracking=True)

    amount = fields.Monetary(string="Amount", required=True, tracking=True)
    currency_id = fields.Many2one(compute="_compute_bucket_company", store=True, comodel_name="res.currency")
    company_id = fields.Many2one(compute="_compute_bucket_company", store=True, comodel_name="res.company")

    reason = fields.Text(string="Reason")
    request_date = fields.Date(string="Request Date", required=True, default=fields.Date.context_today)
    attachment_ids = fields.Many2many("ir.attachment", string="Attachments")

    source_name = fields.Char(compute="_compute_endpoint_names", string="From")
    dest_name = fields.Char(compute="_compute_endpoint_names", string="To")

    _sql_constraints = [
        ("amount_positive", "CHECK(amount > 0)", "The transfer amount must be greater than zero."),
    ]

    @api.depends("src_project_id", "src_head_id")
    def _compute_bucket_company(self):
        for rec in self:
            bucket = rec.src_project_id or rec.src_head_id
            rec.currency_id = bucket.currency_id.id if bucket else rec.env.company.currency_id.id
            rec.company_id = bucket.company_id.id if bucket else rec.env.company.id

    @api.depends("src_project_id", "src_head_id", "dest_project_id", "dest_head_id")
    def _compute_endpoint_names(self):
        for rec in self:
            rec.source_name = rec.src_project_id.display_name or rec.src_head_id.display_name or ""
            rec.dest_name = rec.dest_project_id.display_name or rec.dest_head_id.display_name or ""

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("nn.fund.transfer") or _("New")
        return super().create(vals_list)

    @api.constrains("src_project_id", "src_head_id", "dest_project_id", "dest_head_id")
    def _check_endpoints(self):
        for rec in self:
            if bool(rec.src_project_id) == bool(rec.src_head_id):
                raise ValidationError(_("The source must be exactly one project or one expense head."))
            if bool(rec.dest_project_id) == bool(rec.dest_head_id):
                raise ValidationError(_("The destination must be exactly one project or one expense head."))
            same_project = rec.src_project_id and rec.src_project_id == rec.dest_project_id
            same_head = rec.src_head_id and rec.src_head_id == rec.dest_head_id
            if same_project or same_head:
                raise ValidationError(_("Source and destination must be different buckets."))

    def _validate_submit(self):
        # Can't transfer more than the source currently has available.
        for rec in self:
            source = rec.src_project_id or rec.src_head_id
            available = source.available
            if rec.currency_id.compare_amounts(rec.amount, available) > 0:
                raise ValidationError(_(
                    "Transfer of %(amount)s exceeds %(src)s's available "
                    "balance of %(available)s.",
                    amount=rec.amount, src=source.display_name, available=available,
                ))
        return True

    def _post_on_submit(self):
        Move = self.env["nn.fund.movement"]
        for rec in self:
            Move._post("transfer_hold", rec.amount, rec,
                       project=rec.src_project_id, expense_head=rec.src_head_id)
        return True

    def _post_on_approve(self):
        Move = self.env["nn.fund.movement"]
        for rec in self:
            # Clear the source hold (money leaves)...
            Move._post("transfer_settle", rec.amount, rec,
                       project=rec.src_project_id, expense_head=rec.src_head_id)
            # ...and land it in the destination.
            Move._post("transfer_in", rec.amount, rec,
                       project=rec.dest_project_id, expense_head=rec.dest_head_id)
        return True

    def _post_on_reject(self):
        Move = self.env["nn.fund.movement"]
        for rec in self:
            Move._post("transfer_release", rec.amount, rec,
                       project=rec.src_project_id, expense_head=rec.src_head_id)
        return True
