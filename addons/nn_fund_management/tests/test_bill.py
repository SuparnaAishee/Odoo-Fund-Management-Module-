# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import FundCase


@tagged("post_install", "-at_install")
class TestBill(FundCase):

    def setUp(self):
        super().setUp()
        self.fund_project(self.project, 1000000)
        self.req = self.Requisition.create({
            "project_id": self.project.id, "amount": 500000,
            "requested_by": self.fund_user.id,
        })
        self.approve_full(self.req)

    def test_partial_bill_reduces_billable(self):
        self.Bill.create({"requisition_id": self.req.id, "amount": 200000}).action_post()
        self.assertEqual(self.req.remaining_billable, 300000)
        self.assertEqual(self.project.spent, 200000)

    def test_multiple_partials_allowed(self):
        self.Bill.create({"requisition_id": self.req.id, "amount": 200000}).action_post()
        self.Bill.create({"requisition_id": self.req.id, "amount": 200000}).action_post()
        self.assertEqual(self.req.remaining_billable, 100000)

    def test_over_bill_blocked(self):
        bill = self.Bill.create({"requisition_id": self.req.id, "amount": 600000})
        with self.assertRaises(ValidationError):
            bill.action_post()

    def test_total_billed_cannot_exceed_approved(self):
        self.Bill.create({"requisition_id": self.req.id, "amount": 400000}).action_post()
        over = self.Bill.create({"requisition_id": self.req.id, "amount": 200000})
        with self.assertRaises(ValidationError):
            over.action_post()

    def test_only_approved_requisition(self):
        draft_req = self.Requisition.create({
            "project_id": self.project.id, "amount": 100000,
            "requested_by": self.fund_user.id,
        })
        bill = self.Bill.create({"requisition_id": draft_req.id, "amount": 50000})
        with self.assertRaises(ValidationError):
            bill.action_post()

    def test_reverse_restores_billable_without_creating_funds(self):
        bill = self.Bill.create({"requisition_id": self.req.id, "amount": 300000})
        bill.action_post()
        self.assertEqual(self.req.remaining_billable, 200000)
        self.assertEqual(self.project.spent, 300000)
        bill.action_reverse()
        self.assertEqual(bill.state, "cancelled")
        self.assertEqual(self.req.remaining_billable, 500000)
        self.assertEqual(self.project.spent, 0.0)
        # reversal must not inflate the bucket: available unchanged from pre-bill
        self.assertEqual(self.project.available, 500000)

    def test_bill_follows_requisition_bucket(self):
        # a bill can never point at a different bucket than its requisition
        bill = self.Bill.create({"requisition_id": self.req.id, "amount": 100000})
        self.assertEqual(bill.project_id, self.project)
        self.assertFalse(bill.expense_head_id)
