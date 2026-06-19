# -*- coding: utf-8 -*-
{
    "name": "NN Fund Management",
    "version": "17.0.1.0.0",
    "summary": "Allocate, hold, requisition, bill and transfer funds with a GM→MD "
               "approval chain, built on an append-only fund-movement ledger.",
    "description": """
NN Services Fund Management
===========================
Control how every taka is allocated, held, spent and transferred, with two-level
(GM → MD) approval, so the same money can never be allocated, transferred or spent
more than once. All balances are computed sums over an immutable ledger
(``nn.fund.movement``); no balance is ever edited by hand.
""",
    "author": "NN Services & Engineering Ltd.",
    "website": "https://github.com/SuparnaAishee/Odoo-Fund-Management-Module-",
    "category": "Accounting/Finance",
    "license": "LGPL-3",
    "depends": ["base", "mail"],
    "data": [
        "security/groups.xml",
        "security/ir.model.access.csv",
        "security/record_rules.xml",
        "data/ir_sequence.xml",
        "data/expense_head_data.xml",
        "data/dashboard_data.xml",
        "data/approval_rule_data.xml",
        "data/mail_alias.xml",
        "views/fund_account_views.xml",
        "views/incoming_fund_views.xml",
        "views/bank_email_views.xml",
        "views/project_views.xml",
        "views/expense_head_views.xml",
        "views/fund_movement_views.xml",
        "views/fund_allocation_views.xml",
        "views/fund_requisition_views.xml",
        "views/fund_bill_views.xml",
        "views/fund_transfer_views.xml",
        "views/fund_dashboard_views.xml",
        "views/approval_rule_views.xml",
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "nn_fund_management/static/src/scss/fund_theme.scss",
        ],
    },
    "demo": [
        "demo/demo_users.xml",
    ],
    "application": True,
    "installable": True,
}
