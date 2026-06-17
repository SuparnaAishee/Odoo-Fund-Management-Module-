# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import FundCase


@tagged("post_install", "-at_install")
class TestRequisition(FundCase):

    def setUp(self):
        super().setUp()
        # leave 1,000,000 available on the project to requisition against
        self.fund_project(self.project, 1000000)

    def _req(self, amount):
        return self.Requisition.create({
            "project_id": self.project.id, "amount": amount,
            "requested_by": self.fund_user.id,
        })

    def test_hold_on_submit(self):
        req = self._req(400000)
        req.action_submit()
        self.assertEqual(self.project.requisition_hold, 400000)
        self.assertEqual(self.project.available, 600000)

    def test_reserved_on_approve(self):
        req = self._req(400000)
        self.approve_full(req)
        self.assertEqual(req.state, "approved")
        self.assertEqual(req.remaining_billable, 400000)
        # still held, not yet spent
        self.assertEqual(self.project.requisition_hold, 400000)

    def test_release_on_reject(self):
        req = self._req(400000)
        req.action_submit()
        req.with_user(self.gm_user).action_reject()
        self.assertEqual(self.project.available, 1000000)
        self.assertEqual(self.project.requisition_hold, 0.0)

    def test_over_requisition_blocked(self):
        req = self._req(1500000)
        with self.assertRaises(ValidationError):
            req.action_submit()

    def test_close_releases_unused(self):
        req = self._req(400000)
        self.approve_full(req)
        self.Bill.create({"requisition_id": req.id, "amount": 100000}).action_post()
        self.assertEqual(req.remaining_billable, 300000)
        req.action_close()
        self.assertEqual(req.state, "closed")
        self.assertEqual(req.remaining_billable, 0.0)
        # the unbilled 300k returns to available; only 100k stays held (as spent)
        self.assertEqual(self.project.available, 900000)
        self.assertEqual(self.project.spent, 100000)

    def test_only_approved_can_close(self):
        req = self._req(400000)
        with self.assertRaises(UserError):
            req.action_close()
