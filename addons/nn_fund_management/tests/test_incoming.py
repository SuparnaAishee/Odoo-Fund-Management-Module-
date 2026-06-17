# -*- coding: utf-8 -*-
from psycopg2 import IntegrityError

from odoo.exceptions import UserError
from odoo.tools import mute_logger
from odoo.tests import tagged

from .common import FundCase


@tagged("post_install", "-at_install")
class TestIncoming(FundCase):

    def test_confirm_raises_unassigned(self):
        self.assertEqual(self.account.unassigned, 0.0)
        self.deposit(1000000)
        self.assertEqual(self.account.received, 1000000)
        self.assertEqual(self.account.unassigned, 1000000)

    def test_confirm_posts_single_ledger_line(self):
        inc = self.deposit(500000)
        moves = self.Movement.search([
            ("origin_model", "=", "nn.incoming.fund"), ("origin_id", "=", inc.id)])
        self.assertEqual(len(moves), 1)
        self.assertEqual(moves.move_type, "incoming")

    def test_confirmed_cannot_reset_to_draft(self):
        inc = self.deposit(100000)
        with self.assertRaises(UserError):
            inc.action_draft()

    def test_duplicate_txn_reference_blocked(self):
        self.deposit(100000, ref="DUP")
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            with self.cr.savepoint():
                self.Incoming.create({
                    "fund_account_id": self.account.id, "amount": 200000,
                    "transaction_reference": "DUP",
                })

    def test_amount_must_be_positive(self):
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            with self.cr.savepoint():
                self.Incoming.create({
                    "fund_account_id": self.account.id, "amount": 0,
                    "transaction_reference": "ZERO",
                })
