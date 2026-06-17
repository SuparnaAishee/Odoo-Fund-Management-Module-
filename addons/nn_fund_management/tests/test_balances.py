# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import FundCase


@tagged("post_install", "-at_install")
class TestBalances(FundCase):

    def test_account_balance_identity(self):
        self.deposit(1000000)
        self.approve_full(self.allocate(600000, project=self.project))
        # received == unassigned + on_hold + assigned
        self.assertEqual(
            self.account.received,
            self.account.unassigned + self.account.on_hold + self.account.assigned,
        )

    def test_bucket_conservation(self):
        self.fund_project(self.project, 1000000)
        p = self.project
        # allocated + transfers_in == available + holds + spent + transfers_out
        left = p.allocated + p.transfer_in
        right = (p.available + p.requisition_hold + p.transfer_hold
                 + p.spent + p.transfer_out)
        self.assertAlmostEqual(left, right, places=2)

    def test_balances_are_readonly_computed(self):
        # computed balance fields are not stored-editable: writing is refused
        self.fund_project(self.project, 500000)
        field = self.project._fields["available"]
        self.assertTrue(field.compute)
        self.assertFalse(field.inverse)

    def test_ledger_is_immutable(self):
        self.deposit(100000)
        move = self.Movement.search([("move_type", "=", "incoming")], limit=1)
        with self.assertRaises(UserError):
            move.write({"amount": 1})
        with self.assertRaises(UserError):
            move.unlink()
