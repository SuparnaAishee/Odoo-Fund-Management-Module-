# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import FundCase


@tagged("post_install", "-at_install")
class TestTransfer(FundCase):

    def setUp(self):
        super().setUp()
        self.fund_project(self.project, 1000000)

    def _transfer(self, amount, src=None, dest=None):
        return self.Transfer.create({
            "src_project_id": (src or self.project).id,
            "dest_project_id": (dest or self.project2).id,
            "amount": amount, "requested_by": self.fund_user.id,
        })

    def test_source_and_destination_must_differ(self):
        with self.assertRaises(ValidationError):
            self._transfer(100000, src=self.project, dest=self.project)

    def test_hold_on_submit(self):
        tr = self._transfer(300000)
        tr.action_submit()
        self.assertEqual(self.project.transfer_hold, 300000)
        self.assertEqual(self.project.available, 700000)
        # destination unaffected while pending
        self.assertEqual(self.project2.available, 0.0)

    def test_move_on_approve(self):
        tr = self._transfer(300000)
        self.approve_full(tr)
        self.assertEqual(tr.state, "approved")
        self.assertEqual(self.project.transfer_hold, 0.0)
        self.assertEqual(self.project.transfer_out, 300000)
        self.assertEqual(self.project.available, 700000)
        self.assertEqual(self.project2.transfer_in, 300000)
        self.assertEqual(self.project2.available, 300000)

    def test_return_on_reject(self):
        tr = self._transfer(300000)
        tr.action_submit()
        tr.with_user(self.gm_user).action_reject()
        self.assertEqual(self.project.available, 1000000)
        self.assertEqual(self.project.transfer_hold, 0.0)

    def test_over_transfer_blocked(self):
        tr = self._transfer(1500000)
        with self.assertRaises(ValidationError):
            tr.action_submit()

    def test_held_transfer_funds_cannot_be_reused(self):
        # hold 800k for a transfer, only 200k remains -> a second 800k must fail
        self._transfer(800000).action_submit()
        second = self._transfer(800000)
        with self.assertRaises(ValidationError):
            second.action_submit()
