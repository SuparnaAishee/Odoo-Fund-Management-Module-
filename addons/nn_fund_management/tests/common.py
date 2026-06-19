# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class FundCase(TransactionCase):
    """Shared fixtures: master data plus one user per role, so tests can drive
    the real workflow (submit as requester, approve as GM/MD, etc.)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Account = cls.env["nn.fund.account"]
        cls.Project = cls.env["nn.project"]
        cls.Head = cls.env["nn.expense.head"]
        cls.Incoming = cls.env["nn.incoming.fund"]
        cls.Allocation = cls.env["nn.fund.allocation"]
        cls.Requisition = cls.env["nn.fund.requisition"]
        cls.Bill = cls.env["nn.fund.bill"]
        cls.Transfer = cls.env["nn.fund.transfer"]
        cls.Movement = cls.env["nn.fund.movement"]
        cls.Rule = cls.env["nn.approval.rule"]

        cls.company = cls.env.company
        cls.currency = cls.company.currency_id

        def mk_user(name, login, group_xmlid):
            return cls.env["res.users"].create({
                "name": name,
                "login": login,
                "groups_id": [(4, cls.env.ref(group_xmlid).id)],
            })

        cls.fund_user = mk_user("Test Fund User", "t_fund", "nn_fund_management.group_fund_user")
        cls.finance_user = mk_user("Test Finance", "t_finance", "nn_fund_management.group_finance_user")
        cls.gm_user = mk_user("Test GM", "t_gm", "nn_fund_management.group_gm_approver")
        cls.md_user = mk_user("Test MD", "t_md", "nn_fund_management.group_md_approver")
        # A Fund Administrator who can also approve at both levels, used to
        # exercise the authorised-exception paths (self-approval, cancel-approved).
        cls.admin_user = mk_user("Test Admin", "t_admin", "nn_fund_management.group_fund_admin")
        cls.admin_user.groups_id = [
            (4, cls.env.ref("nn_fund_management.group_gm_approver").id),
            (4, cls.env.ref("nn_fund_management.group_md_approver").id),
        ]
        # A finance user who is *also* an approver but NOT an administrator: can
        # raise and submit requests, yet must still be blocked from approving
        # their own (self-approval is reserved for the admin role).
        cls.approver_user = mk_user("Test Approver", "t_approver", "nn_fund_management.group_finance_user")
        cls.approver_user.groups_id = [
            (4, cls.env.ref("nn_fund_management.group_gm_approver").id),
            (4, cls.env.ref("nn_fund_management.group_md_approver").id),
        ]

        cls.account = cls.Account.create({
            "name": "Test Bank", "account_type": "bank",
            "currency_id": cls.currency.id, "company_id": cls.company.id,
        })
        cls.project = cls.Project.create({
            "name": "Project X", "currency_id": cls.currency.id, "company_id": cls.company.id,
        })
        cls.project2 = cls.Project.create({
            "name": "Project Y", "currency_id": cls.currency.id, "company_id": cls.company.id,
        })
        cls.head = cls.Head.create({
            "name": "Salaries", "currency_id": cls.currency.id, "company_id": cls.company.id,
        })

    # -- helpers ----------------------------------------------------------- #
    def deposit(self, amount, ref="TXN-1"):
        inc = self.Incoming.create({
            "fund_account_id": self.account.id, "amount": amount,
            "transaction_reference": ref,
        })
        inc.with_user(self.finance_user).action_confirm()
        return inc

    def allocate(self, amount, project=None, head=None, requested_by=None):
        vals = {
            "fund_account_id": self.account.id, "amount": amount,
            "requested_by": (requested_by or self.fund_user).id,
        }
        if project:
            vals["project_id"] = project.id
        if head:
            vals["expense_head_id"] = head.id
        return self.Allocation.create(vals)

    def approve_full(self, rec):
        """Drive a request through the default GM -> MD chain."""
        rec.action_submit()
        rec.with_user(self.gm_user).action_approve()
        rec.with_user(self.md_user).action_approve()
        return rec

    def fund_project(self, project, amount):
        """Deposit + allocate + approve, leaving `amount` available on a bucket."""
        self.deposit(amount, ref="DEP-%s-%s" % (project.id, amount))
        alloc = self.allocate(amount, project=project)
        return self.approve_full(alloc)
