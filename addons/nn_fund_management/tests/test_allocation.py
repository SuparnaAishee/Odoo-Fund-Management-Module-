# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import FundCase


@tagged("post_install", "-at_install")
class TestAllocation(FundCase):

    def setUp(self):
        super().setUp()
        self.deposit(1000000)

    def test_target_is_project_xor_head(self):
        # both set -> blocked
        with self.assertRaises(ValidationError):
            self.Allocation.create({
                "fund_account_id": self.account.id, "amount": 100,
                "project_id": self.project.id, "expense_head_id": self.head.id,
            })._check_single_target()
        # neither set -> blocked
        with self.assertRaises(ValidationError):
            self.Allocation.create({
                "fund_account_id": self.account.id, "amount": 100,
            })._check_single_target()

    def test_hold_on_submit(self):
        alloc = self.allocate(600000, project=self.project)
        alloc.action_submit()
        self.assertEqual(self.account.unassigned, 400000)
        self.assertEqual(self.account.on_hold, 600000)
        # nothing assigned to the project yet
        self.assertEqual(self.project.allocated, 0.0)

    def test_assign_on_approve(self):
        alloc = self.allocate(600000, project=self.project)
        self.approve_full(alloc)
        self.assertEqual(alloc.state, "approved")
        self.assertEqual(self.account.on_hold, 0.0)
        self.assertEqual(self.account.assigned, 600000)
        self.assertEqual(self.account.unassigned, 400000)
        self.assertEqual(self.project.allocated, 600000)
        self.assertEqual(self.project.available, 600000)

    def test_release_on_reject(self):
        alloc = self.allocate(600000, project=self.project)
        alloc.action_submit()
        alloc.with_user(self.gm_user).action_reject()
        self.assertEqual(alloc.state, "rejected")
        self.assertEqual(self.account.unassigned, 1000000)
        self.assertEqual(self.account.on_hold, 0.0)

    def test_release_on_cancel(self):
        alloc = self.allocate(600000, project=self.project)
        alloc.action_submit()
        alloc.action_cancel()
        self.assertEqual(alloc.state, "cancelled")
        self.assertEqual(self.account.unassigned, 1000000)

    def test_over_allocation_blocked(self):
        alloc = self.allocate(1500000, project=self.project)
        with self.assertRaises(ValidationError):
            alloc.action_submit()

    def test_held_funds_cannot_be_allocated_again(self):
        # hold 600k, only 400k remains unassigned -> a second 600k must fail
        self.allocate(600000, project=self.project).action_submit()
        second = self.allocate(600000, project=self.project2)
        with self.assertRaises(ValidationError):
            second.action_submit()
