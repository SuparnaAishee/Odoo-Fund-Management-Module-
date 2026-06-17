# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

# Each rule line maps to one approval stage. Codes match nn.approval.line.level
# and resolve to the security group that may decide at that stage.
LEVEL_GROUP = {
    "gm": "nn_fund_management.group_gm_approver",
    "finance": "nn_fund_management.group_finance_user",
    "md": "nn_fund_management.group_md_approver",
}


class ApprovalRule(models.Model):
    """A configurable approval chain selected by request type, amount band and
    company. When a request needs approval, the engine picks the best-matching
    rule and approves through its ordered lines instead of the fixed GM->MD
    default. With no rule, the default GM->MD chain applies."""

    _name = "nn.approval.rule"
    _description = "Approval Rule"
    _order = "sequence, min_amount, id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    model_name = fields.Selection(
        [
            ("nn.fund.allocation", "Fund Allocation"),
            ("nn.fund.requisition", "Fund Requisition"),
            ("nn.fund.transfer", "Fund Transfer"),
        ],
        string="Applies To",
        help="Leave empty to apply to every request type.",
    )
    company_id = fields.Many2one(
        "res.company", string="Company",
        help="Leave empty to apply to every company.",
    )
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id,
    )
    min_amount = fields.Monetary(string="Minimum Amount", default=0.0)
    max_amount = fields.Monetary(
        string="Maximum Amount", default=0.0,
        help="Upper bound of the band. Use 0 for no upper limit.",
    )
    line_ids = fields.One2many("nn.approval.rule.line", "rule_id", string="Approval Levels")

    @api.constrains("line_ids")
    def _check_line_count(self):
        for rule in self:
            if len(rule.line_ids) > 3:
                raise ValidationError(_(
                    "An approval rule supports at most three levels."
                ))
            if not rule.line_ids:
                raise ValidationError(_("Define at least one approval level."))

    @api.constrains("min_amount", "max_amount")
    def _check_band(self):
        for rule in self:
            if rule.max_amount and rule.max_amount < rule.min_amount:
                raise ValidationError(_(
                    "Maximum amount must be greater than the minimum amount."
                ))

    @api.model
    def _match_for(self, record):
        """Return the best rule for a request, or an empty recordset."""
        amount = record.amount
        rules = self.search([
            ("min_amount", "<=", amount),
            "|", ("model_name", "=", record._name), ("model_name", "=", False),
        ])
        candidates = []
        for rule in rules:
            if rule.max_amount and amount > rule.max_amount:
                continue
            if rule.company_id and rule.company_id != record.company_id:
                continue
            candidates.append(rule)
        if not candidates:
            return self.browse()
        # Most specific wins: matched model, matched company, tightest band.
        candidates.sort(key=lambda r: (
            bool(r.model_name), bool(r.company_id), r.min_amount, -r.sequence,
        ), reverse=True)
        return candidates[0]


class ApprovalRuleLine(models.Model):
    _name = "nn.approval.rule.line"
    _description = "Approval Rule Level"
    _order = "sequence, id"

    rule_id = fields.Many2one("nn.approval.rule", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    level = fields.Selection(
        [("gm", "GM Approver"), ("finance", "Finance User"), ("md", "MD Approver")],
        string="Approver Level", required=True,
    )
