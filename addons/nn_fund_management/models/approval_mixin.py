# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError, ValidationError

# Each level is (code, approver group, the state where this level decides).
# Kept as data rather than hardcoded users so the chain can be overridden later.
DEFAULT_LEVELS = [
    ("gm", "nn_fund_management.group_gm_approver", "submitted"),
    ("md", "nn_fund_management.group_md_approver", "gm_approval"),
]


class ApprovalMixin(models.AbstractModel):
    """GM -> MD approval state machine shared by allocation, requisition and
    transfer. Concrete models implement the ``_post_on_*`` hooks to post their
    own ledger lines; the mixin owns the workflow and guards."""

    _name = "nn.approval.mixin"
    _description = "Approval Mixin"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("gm_approval", "GM Approved"),
            ("md_approval", "MD Approved"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        string="Status", default="draft", required=True, tracking=True, copy=False,
    )
    requested_by = fields.Many2one(
        "res.users", string="Requested By", required=True, tracking=True,
        default=lambda self: self.env.user, copy=False,
    )
    current_level = fields.Char(
        string="Pending Level", compute="_compute_current_level",
    )
    approval_line_ids = fields.One2many(
        "nn.approval.line", compute="_compute_approval_lines", string="Approval History",
    )
    posted = fields.Boolean(
        string="Final Effect Posted", default=False, copy=False, readonly=True,
        help="Guards against posting the final money effect more than once.",
    )

    # Override these for a per-type or amount-banded approval chain.
    def _approval_levels(self):
        return DEFAULT_LEVELS

    def _allow_self_approval(self):
        return False

    # Concrete models post their ledger lines through these hooks.
    def _validate_submit(self):
        return True

    def _post_on_submit(self):
        """Post the hold lines."""
        return True

    def _post_on_approve(self):
        """Post the final effect (assign / reserve / transfer_in)."""
        return True

    def _post_on_reject(self):
        """Release the hold. Reused on cancel."""
        return True

    def _post_on_cancel(self):
        return self._post_on_reject()

    def _compute_current_level(self):
        for rec in self:
            level = rec._current_level()
            rec.current_level = level[0] if level else False

    def _compute_approval_lines(self):
        Line = self.env["nn.approval.line"]
        for rec in self:
            if isinstance(rec.id, int):
                rec.approval_line_ids = Line.search(
                    [("res_model", "=", rec._name), ("res_id", "=", rec.id)]
                )
            else:
                rec.approval_line_ids = Line.browse()

    def _current_level(self):
        """The level whose pending state matches the record's state, else False."""
        self.ensure_one()
        for level in self._approval_levels():
            if level[2] == self.state:
                return level
        return False

    def _check_approver(self, level):
        self.ensure_one()
        code, group_xmlid, _state = level
        if not self.env.user.has_group(group_xmlid):
            raise AccessError(_(
                "Only a %s approver may act at this stage.", code.upper()
            ))
        if self.env.user == self.requested_by and not self._allow_self_approval():
            raise UserError(_("You cannot approve or reject your own request."))

    def _add_approval_line(self, level_code, result, comment):
        self.ensure_one()
        self.env["nn.approval.line"].create({
            "res_model": self._name,
            "res_id": self.id,
            "approver_id": self.env.user.id,
            "level": level_code,
            "result": result,
            "comment": comment or False,
        })
        body = _("%(result)s at %(level)s level") % {
            "result": dict(self.env["nn.approval.line"]._fields["result"].selection)[result],
            "level": level_code.upper(),
        }
        if comment:
            body += ": " + comment
        self.message_post(body=body)

    def action_submit(self):
        # Queue tracking mails instead of force-sending, so a missing outgoing
        # mail server never breaks the workflow.
        self = self.with_context(mail_notify_force_send=False)
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only a draft request can be submitted."))
            rec._validate_submit()
            rec.state = "submitted"
            rec._post_on_submit()
        return True

    def action_approve(self):
        self = self.with_context(mail_notify_force_send=False)
        for rec in self:
            level = rec._current_level()
            if not level:
                raise UserError(_("This request is not awaiting approval."))
            rec._check_approver(level)
            # Approvers only have read access to the document, so the state and
            # ledger writes run as superuser. The decision stays attributed to
            # the acting user via the approval line above.
            rec_su = rec.sudo()
            rec_su._add_approval_line(level[0], "approved", self.env.context.get("approval_comment"))

            levels = rec._approval_levels()
            codes = [lvl[0] for lvl in levels]
            idx = codes.index(level[0])
            if idx == len(levels) - 1:
                if not rec_su.posted:
                    rec_su._post_on_approve()
                    rec_su.posted = True
                rec_su.state = "approved"
            else:
                rec_su.state = levels[idx + 1][2]
        return True

    def action_reject(self):
        self = self.with_context(mail_notify_force_send=False)
        for rec in self:
            level = rec._current_level()
            if not level:
                raise UserError(_("This request is not awaiting approval."))
            rec._check_approver(level)
            rec_su = rec.sudo()
            rec_su._add_approval_line(level[0], "rejected", self.env.context.get("approval_comment"))
            rec_su.state = "rejected"
            rec_su._post_on_reject()
        return True

    def action_cancel(self):
        self = self.with_context(mail_notify_force_send=False)
        for rec in self:
            if rec.state in ("approved", "rejected", "cancelled"):
                raise UserError(_(
                    "A finalised request cannot be cancelled; post a reversal instead."
                ))
            had_hold = rec.state in ("submitted", "gm_approval", "md_approval")
            if had_hold:
                rec._post_on_cancel()
            rec.state = "cancelled"
        return True

    def action_reset_to_draft(self):
        for rec in self:
            if rec.state not in ("rejected", "cancelled"):
                raise UserError(_("Only rejected or cancelled requests can be reset to draft."))
            rec.state = "draft"
        return True
