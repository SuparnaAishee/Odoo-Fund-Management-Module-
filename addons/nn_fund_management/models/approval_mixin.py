# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError, ValidationError

# Ordered approval chain. Each level: (code, group external id, the state in
# which this level is the *current* approver). The chain is intentionally data,
# not hardcoded user IDs (BR-16); the bonus rule engine can later override
# ``_approval_levels`` per request type / amount band.
DEFAULT_LEVELS = [
    ("gm", "nn_fund_management.group_gm_approver", "submitted"),
    ("md", "nn_fund_management.group_md_approver", "gm_approval"),
]


class ApprovalMixin(models.AbstractModel):
    """Reusable GM -> MD approval state machine shared by allocation,
    requisition and transfer. Concrete models implement the ``_post_on_*``
    hooks to post their own ledger lines; the mixin owns the workflow, the
    guards (BR-13..16) and the idempotency (BR-03)."""

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
        help="Idempotency guard: the final money effect posts at most once (BR-03).",
    )

    # ------------------------------------------------------------------ #
    # Configuration hooks (override for the bonus rule engine)
    # ------------------------------------------------------------------ #
    def _approval_levels(self):
        return DEFAULT_LEVELS

    def _allow_self_approval(self):
        # BR-15: a user may not approve their own request unless flagged.
        return False

    # ------------------------------------------------------------------ #
    # Concrete-model hooks (post ledger lines)
    # ------------------------------------------------------------------ #
    def _validate_submit(self):
        """Raise ValidationError if the request may not be submitted."""
        return True

    def _post_on_submit(self):
        """Post HOLD ledger lines."""
        return True

    def _post_on_approve(self):
        """Post the final effect (assign / reserve / transfer_in)."""
        return True

    def _post_on_reject(self):
        """Post RELEASE ledger lines (also reused on cancel)."""
        return True

    def _post_on_cancel(self):
        return self._post_on_reject()

    # ------------------------------------------------------------------ #
    # Computed
    # ------------------------------------------------------------------ #
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

    # ------------------------------------------------------------------ #
    # Level resolution & guards
    # ------------------------------------------------------------------ #
    def _current_level(self):
        """Return the (code, group, pending_state) tuple whose pending_state ==
        the record's current state, or False if not awaiting a decision."""
        self.ensure_one()
        for level in self._approval_levels():
            if level[2] == self.state:
                return level
        return False

    def _check_approver(self, level):
        """Server-side approval guards (BR-13..15), independent of button
        visibility (BR-38)."""
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

    # ------------------------------------------------------------------ #
    # Workflow actions
    # ------------------------------------------------------------------ #
    def action_submit(self):
        # Queue tracking notifications rather than force-sending them, so the
        # workflow never fails just because no outgoing mail server is set up.
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
            # Authorize as the *real* user (group + self-approval guards)...
            rec._check_approver(level)
            # ...then perform the privileged writes with elevated rights, since
            # an approver only holds read access to the document (BR-38). sudo()
            # keeps the acting user, so the decision is still attributed to them.
            rec_su = rec.sudo()
            rec_su._add_approval_line(level[0], "approved", self.env.context.get("approval_comment"))

            levels = rec._approval_levels()
            codes = [lvl[0] for lvl in levels]
            idx = codes.index(level[0])
            if idx == len(levels) - 1:
                # Final approver: post the money effect exactly once (BR-03).
                if not rec_su.posted:
                    rec_su._post_on_approve()
                    rec_su.posted = True
                rec_su.state = "approved"
            else:
                # Advance to the state where the next level is the approver.
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
