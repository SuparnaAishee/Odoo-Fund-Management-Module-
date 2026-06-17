# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import FundCase


@tagged("post_install", "-at_install")
class TestDemoScenario(FundCase):
    """End-to-end replay of the PDF Sample Demonstration (§13)."""

    def test_full_scenario(self):
        A, B = self.project, self.project2

        # 1. receive 1,000,000
        self.deposit(1000000)
        self.assertEqual(self.account.unassigned, 1000000)

        # 2-3. allocate 600,000 to A, submit -> held while pending
        alloc = self.allocate(600000, project=A)
        alloc.action_submit()
        self.assertEqual(self.account.on_hold, 600000)
        self.assertEqual(self.account.unassigned, 400000)

        # 4. reject -> money returns
        alloc.with_user(self.gm_user).action_reject()
        self.assertEqual(self.account.unassigned, 1000000)

        # 5. resubmit + approve -> A funded
        alloc2 = self.allocate(600000, project=A)
        self.approve_full(alloc2)
        self.assertEqual(A.available, 600000)

        # 6-7. transfer 200,000 A -> B, held while pending
        tr = self.Transfer.create({
            "src_project_id": A.id, "dest_project_id": B.id,
            "amount": 200000, "requested_by": self.fund_user.id,
        })
        tr.action_submit()
        self.assertEqual(A.transfer_hold, 200000)
        self.assertEqual(A.available, 400000)

        # 8. approve transfer -> lands in B
        tr.with_user(self.gm_user).action_approve()
        tr.with_user(self.md_user).action_approve()
        self.assertEqual(B.available, 200000)
        self.assertEqual(A.available, 400000)

        # 9. requisition 150,000 on B
        req = self.Requisition.create({
            "project_id": B.id, "amount": 150000, "requested_by": self.fund_user.id,
        })
        self.approve_full(req)
        self.assertEqual(req.remaining_billable, 150000)

        # 10-11. partial bill 100,000 -> 50,000 remains billable
        self.Bill.create({"requisition_id": req.id, "amount": 100000}).action_post()
        self.assertEqual(req.remaining_billable, 50000)
        self.assertEqual(B.spent, 100000)

        # 12. a 60,000 bill is blocked (only 50,000 left)
        over = self.Bill.create({"requisition_id": req.id, "amount": 60000})
        with self.assertRaises(ValidationError):
            over.action_post()

        # 13. B's requisition is bound to B; a bill on it can never spend A
        bill = self.Bill.create({"requisition_id": req.id, "amount": 10000})
        self.assertEqual(bill.project_id, B)
        self.assertNotEqual(bill.project_id, A)
