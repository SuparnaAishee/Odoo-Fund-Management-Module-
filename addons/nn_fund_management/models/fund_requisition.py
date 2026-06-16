# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class FundRequisition(models.Model):
    """Request funds *from* a project/head. Hold on submit, keep reserved on
    approve, bill against it (Phase 6), release the unused part on close
    (PDF section 6)."""

    _name = "nn.fund.requisition"
    _description = "Fund Requisition"
    _inherit = ["nn.approval.mixin"]
    _order = "request_date desc, id desc"

    name = fields.Char(string="Reference", required=True, copy=False, readonly=True, default=lambda self: _("New"))
    project_id = fields.Many2one("nn.project", string="Project", tracking=True)
    expense_head_id = fields.Many2one("nn.expense.head", string="Expense Head", tracking=True)
    amount = fields.Monetary(string="Requested Amount", required=True, tracking=True)
    currency_id = fields.Many2one(compute="_compute_bucket_company", store=True, comodel_name="res.currency")
    company_id = fields.Many2one(compute="_compute_bucket_company", store=True, comodel_name="res.company")

    purpose = fields.Text(string="Purpose")
    request_date = fields.Date(string="Request Date", required=True, default=fields.Date.context_today)
    required_date = fields.Date(string="Required Date")
    attachment_ids = fields.Many2many("ir.attachment", string="Attachments")

    target_name = fields.Char(string="Target", compute="_compute_target_name")
    remaining_billable = fields.Monetary(
        string="Remaining Billable", compute="_compute_remaining_billable", store=True,
        help="Approved amount still available to bill against.",
    )

    # Extend the shared approval state machine with a 'closed' terminal state.
    state = fields.Selection(
        selection_add=[("closed", "Closed")],
        ondelete={"closed": "set default"},
    )

    _sql_constraints = [
        ("amount_positive", "CHECK(amount > 0)", "The requisition amount must be greater than zero."),
    ]

    @api.depends("project_id", "expense_head_id")
    def _compute_bucket_company(self):
        for rec in self:
            bucket = rec.project_id or rec.expense_head_id
            rec.currency_id = bucket.currency_id.id if bucket else rec.env.company.currency_id.id
            rec.company_id = bucket.company_id.id if bucket else rec.env.company.id

    @api.depends("project_id", "expense_head_id")
    def _compute_target_name(self):
        for rec in self:
            rec.target_name = rec.project_id.display_name or rec.expense_head_id.display_name or ""

    @api.depends("state", "amount")
    def _compute_remaining_billable(self):
        # Phase 6 extends this to subtract billed amounts; until a bill exists
        # the full approved amount is billable. Only an *approved* (not yet
        # closed) requisition has anything left to bill.
        for rec in self:
            rec.remaining_billable = rec.amount if rec.state == "approved" else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("nn.fund.requisition") or _("New")
        return super().create(vals_list)

    @api.constrains("project_id", "expense_head_id")
    def _check_single_target(self):
        for rec in self:
            if bool(rec.project_id) == bool(rec.expense_head_id):
                raise ValidationError(_(
                    "A requisition must target exactly one of a project or an "
                    "expense head (never both, never neither)."
                ))

    def _bucket(self):
        self.ensure_one()
        return self.project_id, self.expense_head_id

    # -- Approval-mixin hooks ---------------------------------------------- #
    def _validate_submit(self):
        # BR-20: cannot hold more than the bucket currently has available.
        for rec in self:
            bucket = rec.project_id or rec.expense_head_id
            available = bucket.available
            if rec.currency_id.compare_amounts(rec.amount, available) > 0:
                raise ValidationError(_(
                    "Requisition of %(amount)s exceeds %(bucket)s's available "
                    "balance of %(available)s.",
                    amount=rec.amount, bucket=bucket.display_name, available=available,
                ))
        return True

    def _post_on_submit(self):
        Move = self.env["nn.fund.movement"]
        for rec in self:
            project, head = rec._bucket()
            Move._post("req_hold", rec.amount, rec, project=project, expense_head=head)
        return True

    def _post_on_approve(self):
        # BR-21: nothing leaves the bucket on approval; the amount simply stays
        # reserved (still held) and becomes billable.
        return True

    def _post_on_reject(self):
        Move = self.env["nn.fund.movement"]
        for rec in self:
            project, head = rec._bucket()
            Move._post("req_release", rec.amount, rec, project=project, expense_head=head)
        return True

    def action_close(self):
        """BR-23: close an approved requisition, releasing any unused (unbilled)
        reservation back to the bucket's available balance."""
        self = self.with_context(mail_notify_force_send=False)
        Move = self.env["nn.fund.movement"]
        for rec in self:
            if rec.state != "approved":
                raise UserError(_("Only an approved requisition can be closed."))
            unused = rec.remaining_billable
            if rec.currency_id.compare_amounts(unused, 0.0) > 0:
                project, head = rec._bucket()
                Move._post("req_release", unused, rec, project=project, expense_head=head)
            rec.state = "closed"
        return True
