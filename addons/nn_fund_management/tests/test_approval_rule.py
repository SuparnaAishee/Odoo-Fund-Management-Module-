# -*- coding: utf-8 -*-
from odoo.tests import tagged

from .common import FundCase


@tagged("post_install", "-at_install")
class TestApprovalRule(FundCase):

    def setUp(self):
        super().setUp()
        self.deposit(2000000)

    def _chain(self, amount):
        alloc = self.allocate(amount, head=self.head)
        return [lvl[0] for lvl in alloc._approval_levels()]

    def test_default_chain_is_gm_md(self):
        # with no active rule, the default GM -> MD applies
        self.assertEqual(self._chain(600000), ["gm", "md"])

    def test_amount_bands_select_chain(self):
        self.Rule.create({"name": "low", "min_amount": 0, "max_amount": 50000,
                          "line_ids": [(0, 0, {"sequence": 1, "level": "gm"})]})
        self.Rule.create({"name": "mid", "min_amount": 50000, "max_amount": 200000,
                          "line_ids": [(0, 0, {"sequence": 1, "level": "gm"}),
                                       (0, 0, {"sequence": 2, "level": "finance"})]})
        self.Rule.create({"name": "high", "min_amount": 200000, "max_amount": 0,
                          "line_ids": [(0, 0, {"sequence": 1, "level": "gm"}),
                                       (0, 0, {"sequence": 2, "level": "finance"}),
                                       (0, 0, {"sequence": 3, "level": "md"})]})
        self.assertEqual(self._chain(30000), ["gm"])
        self.assertEqual(self._chain(100000), ["gm", "finance"])
        self.assertEqual(self._chain(300000), ["gm", "finance", "md"])

    def test_three_level_workflow_runs(self):
        self.Rule.create({"name": "high", "min_amount": 200000, "max_amount": 0,
                          "line_ids": [(0, 0, {"sequence": 1, "level": "gm"}),
                                       (0, 0, {"sequence": 2, "level": "finance"}),
                                       (0, 0, {"sequence": 3, "level": "md"})]})
        alloc = self.allocate(300000, head=self.head)
        alloc.action_submit()
        alloc.with_user(self.gm_user).action_approve()
        self.assertEqual(alloc.state, "gm_approval")
        alloc.with_user(self.finance_user).action_approve()
        self.assertEqual(alloc.state, "md_approval")
        alloc.with_user(self.md_user).action_approve()
        self.assertEqual(alloc.state, "approved")
        self.assertTrue(alloc.posted)

    def test_rule_requires_at_least_one_level(self):
        from odoo.exceptions import ValidationError
        rule = self.Rule.create({
            "name": "one", "min_amount": 0, "max_amount": 0,
            "line_ids": [(0, 0, {"sequence": 1, "level": "gm"})],
        })
        with self.assertRaises(ValidationError):
            rule.write({"line_ids": [(5, 0, 0)]})
            rule.flush_recordset()
