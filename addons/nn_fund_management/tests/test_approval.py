# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, AccessError
from odoo.tests import tagged

from .common import FundCase


@tagged("post_install", "-at_install")
class TestApproval(FundCase):

    def setUp(self):
        super().setUp()
        self.deposit(1000000)

    def _submitted(self, requested_by=None):
        alloc = self.allocate(600000, project=self.project, requested_by=requested_by)
        alloc.action_submit()
        return alloc

    def test_gm_before_md(self):
        alloc = self._submitted()
        # MD cannot act while the request is at the GM stage
        with self.assertRaises(AccessError):
            alloc.with_user(self.md_user).action_approve()
        # GM first, then MD
        alloc.with_user(self.gm_user).action_approve()
        self.assertEqual(alloc.state, "gm_approval")
        alloc.with_user(self.md_user).action_approve()
        self.assertEqual(alloc.state, "approved")

    def test_only_current_approver(self):
        alloc = self._submitted()
        # a plain fund user may never approve
        with self.assertRaises(AccessError):
            alloc.with_user(self.fund_user).action_approve()

    def test_no_self_approval(self):
        # request raised by the GM; that same GM may not approve it
        alloc = self._submitted(requested_by=self.gm_user)
        with self.assertRaises(UserError):
            alloc.with_user(self.gm_user).action_approve()

    def test_idempotent_no_duplicate_movements(self):
        alloc = self.allocate(600000, project=self.project)
        self.approve_full(alloc)
        assigns = self.Movement.search([
            ("origin_model", "=", alloc._name), ("origin_id", "=", alloc.id),
            ("move_type", "=", "assign")])
        self.assertEqual(len(assigns), 1)
        # re-approving a finalised request is refused and posts nothing new
        with self.assertRaises(UserError):
            alloc.with_user(self.md_user).action_approve()
        assigns2 = self.Movement.search([
            ("origin_model", "=", alloc._name), ("origin_id", "=", alloc.id),
            ("move_type", "=", "assign")])
        self.assertEqual(len(assigns2), 1)

    def test_approval_history_recorded(self):
        alloc = self.allocate(600000, project=self.project)
        self.approve_full(alloc)
        lines = self.env["nn.approval.line"].search([
            ("res_model", "=", alloc._name), ("res_id", "=", alloc.id)])
        self.assertEqual(len(lines), 2)
        self.assertEqual(set(lines.mapped("level")), {"gm", "md"})
        self.assertEqual(set(lines.mapped("result")), {"approved"})
        self.assertEqual(lines.filtered(lambda l: l.level == "gm").approver_id, self.gm_user)
