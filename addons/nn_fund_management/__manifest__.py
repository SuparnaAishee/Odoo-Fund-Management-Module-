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
        "views/menus.xml",
    ],
    "demo": [],
    "application": True,
    "installable": True,
}
