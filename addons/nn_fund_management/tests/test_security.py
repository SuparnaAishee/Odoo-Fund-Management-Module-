# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
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
