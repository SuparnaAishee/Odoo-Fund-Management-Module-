# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import FundCase


@tagged("post_install", "-at_install")
class TestSecurity(FundCase):
    """Server-side access control (PDF §9: hiding buttons is not enough)."""

    def test_only_finance_confirms_incoming(self):
        inc = self.Incoming.create({
            "fund_account_id": self.account.id, "amount": 100000,
            "transaction_reference": "SEC-1",
        })
        # a plain fund user must not be able to confirm a deposit
        with self.assertRaises(AccessError):
            inc.with_user(self.fund_user).action_confirm()
        # finance succeeds
        inc.with_user(self.finance_user).action_confirm()
        self.assertEqual(inc.state, "confirmed")

    def test_fund_user_cannot_approve(self):
        self.deposit(1000000)
        alloc = self.allocate(600000, project=self.project)
        alloc.action_submit()
        with self.assertRaises(AccessError):
            alloc.with_user(self.fund_user).action_approve()

    def test_fund_user_sees_only_own_requests(self):
        self.deposit(1000000)
        mine = self.allocate(100000, project=self.project, requested_by=self.fund_user)
        other = self.allocate(100000, project=self.project2, requested_by=self.finance_user)
        visible = self.Allocation.with_user(self.fund_user).search([])
        self.assertIn(mine, visible)
        self.assertNotIn(other, visible)

    # -- §4: self-approval only for the specially-authorised role ----------- #
    def test_self_approval_blocked_for_non_admin(self):
        """An approver who raised the request cannot approve their own request."""
        self.deposit(1000000)
        alloc = self.allocate(100000, project=self.project, requested_by=self.approver_user)
        alloc.with_user(self.approver_user).action_submit()
        with self.assertRaises(UserError):
            alloc.with_user(self.approver_user).action_approve()

    def test_self_approval_allowed_for_admin(self):
        """A Fund Administrator is the authorised role, so may self-approve."""
        self.deposit(1000000)
        alloc = self.allocate(100000, project=self.project, requested_by=self.admin_user)
        alloc.with_user(self.admin_user).action_submit()
        alloc.with_user(self.admin_user).action_approve()   # GM level
        alloc.with_user(self.admin_user).action_approve()   # MD level
        self.assertEqual(alloc.state, "approved")

    # -- §9: only authorised users cancel approved, and it reverses --------- #
    def test_non_admin_cannot_cancel_approved(self):
        alloc = self.fund_project(self.project, 500000)
        self.assertEqual(alloc.state, "approved")
        with self.assertRaises(UserError):
            alloc.with_user(self.fund_user).action_cancel()

    def test_admin_cancel_approved_reverses_money(self):
        alloc = self.fund_project(self.project, 500000)
        self.assertEqual(self.account.assigned, 500000)
        self.assertEqual(self.project.allocated, 500000)
        self.assertEqual(self.account.unassigned, 0)

        alloc.with_user(self.admin_user).action_cancel()

        self.assertEqual(alloc.state, "cancelled")
        # money is fully reversed: back to unassigned, out of the bucket, and no
        # new funds created (received is unchanged).
        self.assertEqual(self.account.assigned, 0)
        self.assertEqual(self.account.unassigned, 500000)
        self.assertEqual(self.project.allocated, 0)
        self.assertEqual(self.account.received, 500000)
