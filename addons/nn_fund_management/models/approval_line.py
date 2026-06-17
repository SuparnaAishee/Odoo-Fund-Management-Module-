# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ApprovalLine(models.Model):
    """History of one approval decision, stored generically by (res_model,
    res_id) so a single model serves every approvable document."""

    _name = "nn.approval.line"
    _description = "Approval Decision Line"
    _order = "decision_date desc, id desc"

    res_model = fields.Char(string="Document Model", required=True, index=True)
    res_id = fields.Integer(string="Document ID", required=True, index=True)
    document_ref = fields.Reference(
        selection="_selection_document_ref", string="Document",
        compute="_compute_document_ref",
    )

    approver_id = fields.Many2one(
        "res.users", string="Approver", required=True,
        default=lambda self: self.env.user,
    )
    decision_date = fields.Datetime(string="Date", required=True, default=fields.Datetime.now)
    level = fields.Selection(
        [("gm", "GM"), ("md", "MD"), ("finance", "Finance")],
        string="Level", required=True,
    )
    result = fields.Selection(
        [("approved", "Approved"), ("rejected", "Rejected")],
        string="Result", required=True,
    )
    comment = fields.Text(string="Comment")

    @api.model
    def _selection_document_ref(self):
        models_ = self.env["ir.model"].search([("model", "like", "nn.fund.%")])
        return [(m.model, m.name) for m in models_]

    def _compute_document_ref(self):
        for line in self:
            if line.res_model and line.res_id:
                line.document_ref = "%s,%s" % (line.res_model, line.res_id)
            else:
                line.document_ref = False
