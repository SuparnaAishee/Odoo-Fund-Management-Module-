# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class FundAccount(models.Model):
    _name = "nn.fund.account"
    _description = "Fund Account (bank / cash)"
    _order = "name"

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code")
    account_type = fields.Selection(
        [("bank", "Bank"), ("cash", "Cash"), ("other", "Other")],
        string="Type", required=True, default="bank",
    )
    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency", string="Currency", required=True,
        default=lambda self: self.env.company.currency_id,
    )
    active = fields.Boolean(default=True)

    # Optional matching keys so a parsed bank email can auto-route to this
    # account: by bank name and/or the last digits of the account number.
    bank_name = fields.Char(string="Bank Name")
    account_ref = fields.Char(
        string="Account Match Key",
        help="Last digits of the bank account number, used to auto-match "
             "incoming bank-notification emails to this fund account.",
    )

    movement_ids = fields.One2many("nn.fund.movement", "account_id", string="Movements")

    # All balances are computed sums over the ledger, never written by hand.
    received = fields.Monetary(string="Total Received", compute="_compute_balances", store=True)
    unassigned = fields.Monetary(string="Available (Unassigned)", compute="_compute_balances", store=True)
    on_hold = fields.Monetary(string="On Hold", compute="_compute_balances", store=True)
    assigned = fields.Monetary(string="Assigned", compute="_compute_balances", store=True)

    @api.depends("movement_ids.move_type", "movement_ids.amount")
    def _compute_balances(self):
        for account in self:
            sums = dict.fromkeys(
                ("incoming", "alloc_hold", "alloc_release", "assign", "assign_reverse"), 0.0
            )
            for move in account.movement_ids:
                if move.move_type in sums:
                    sums[move.move_type] += move.amount
            account.received = sums["incoming"]
            # An assign_reverse (cancel of an approved allocation) returns the
            # assigned amount to the unassigned pool and clears the assignment.
            account.unassigned = (
                sums["incoming"] - sums["alloc_hold"] + sums["alloc_release"]
                + sums["assign_reverse"]
            )
            account.on_hold = sums["alloc_hold"] - sums["alloc_release"] - sums["assign"]
            account.assigned = sums["assign"] - sums["assign_reverse"]

    @api.constrains("movement_ids")
    def _check_non_negative(self):
        # An account's unassigned and on-hold balances can never go negative.
        for account in self:
            if account.currency_id.compare_amounts(account.unassigned, 0.0) < 0:
                raise ValidationError(_(
                    "Account %s would have a negative unassigned balance.", account.name
                ))
            if account.currency_id.compare_amounts(account.on_hold, 0.0) < 0:
                raise ValidationError(_(
                    "Account %s would have a negative on-hold balance.", account.name
                ))

    # ----------------------------------------------------------------- #
    # Sample data
    # ----------------------------------------------------------------- #
    @api.model
    def _seed_demo_data(self):
        """Populate a fresh deployment with a small, realistic scenario so the
        dashboard shows non-zero balances out of the box (the production install
        runs --without-demo=all, so nothing transactional is loaded otherwise).

        Idempotent: skips entirely once any fund account exists, and runs inside
        a savepoint so a seeding error can never abort the module install/upgrade.
        Called from data/sample_data.xml on install and upgrade.
        """
        if self.search_count([]):
            return
        try:
            with self.env.cr.savepoint():
                self._build_demo_data()
            _logger.info("nn_fund_management: sample data seeded.")
        except Exception as exc:  # never let seeding brick the deploy
            _logger.warning("nn_fund_management: sample data skipped (%s)", exc)

    @api.model
    def _build_demo_data(self):
        # Act as the administrator, who holds every fund role (Finance to confirm
        # deposits, GM+MD to approve, Fund Administrator to self-approve).
        admin = self.env.ref("base.user_admin")
        env = self.env(user=admin.id)
        company = admin.company_id or env.company
        currency = company.currency_id

        account = env["nn.fund.account"].create({
            "name": "Main Operating Account", "code": "MAIN",
            "account_type": "bank",
            "company_id": company.id, "currency_id": currency.id,
        })
        proj_web = env["nn.project"].create({
            "name": "Website Revamp", "code": "WEB",
            "company_id": company.id, "currency_id": currency.id,
        })
        proj_app = env["nn.project"].create({
            "name": "Mobile App", "code": "APP",
            "company_id": company.id, "currency_id": currency.id,
        })

        # 1) Receive 1,000,000 into the account.
        deposit = env["nn.incoming.fund"].create({
            "fund_account_id": account.id, "amount": 1000000.0,
            "transaction_reference": "SEED-DEP-001",
            "sender": "NN Services HQ",
        })
        deposit.action_confirm()

        def allocate(amount, project=None, head=None):
            vals = {"fund_account_id": account.id, "amount": amount}
            if project:
                vals["project_id"] = project.id
            if head:
                vals["expense_head_id"] = head.id
            alloc = env["nn.fund.allocation"].create(vals)
            alloc.action_submit()
            alloc.action_approve()  # GM
            alloc.action_approve()  # MD
            return alloc

        head_salary = env.ref("nn_fund_management.expense_head_salary")
        head_rent = env.ref("nn_fund_management.expense_head_office_rent")
        head_mkt = env.ref("nn_fund_management.expense_head_marketing")

        # 2) Allocate to projects and expense heads (leaves 120,000 unassigned).
        allocate(400000.0, project=proj_web)
        allocate(250000.0, project=proj_app)
        allocate(150000.0, head=head_salary)
        allocate(80000.0, head=head_rent)
        allocate(80000.0, head=head_mkt)

        # 3) Requisition + partial bill on Website Revamp, so it shows real
        #    "spent" and a remaining hold on the dashboard.
        req = env["nn.fund.requisition"].create({
            "project_id": proj_web.id, "amount": 200000.0,
        })
        req.action_submit()
        req.action_approve()  # GM
        req.action_approve()  # MD
        env["nn.fund.bill"].create({
            "requisition_id": req.id, "amount": 120000.0,
            "description": "Phase 1 vendor invoice",
        }).action_post()
