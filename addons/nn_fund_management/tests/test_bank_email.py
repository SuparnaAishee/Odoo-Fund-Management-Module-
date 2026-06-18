# -*- coding: utf-8 -*-
from .common import FundCase

GOOD_SUBJECT = "Transaction Alert: BDT 50,000.00 Credited"
GOOD_BODY = (
    "Dear Customer,\n"
    "Your account XXXXXX1234 with City Bank has been credited.\n"
    "Amount: BDT 50,000.00\n"
    "Transaction Ref: TXN-ABC-001\n"
    "Date: 19-Jun-2026\n"
    "From: ACME TRADING LTD\n"
    "Thank you for banking with us."
)


class TestBankEmail(FundCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.BankEmail = cls.env["nn.bank.email"]
        # Match key so parsed emails auto-route to the shared test account.
        cls.account.write({"bank_name": "City Bank", "account_ref": "1234"})

    def _receive(self, message_id, subject=GOOD_SUBJECT, body=GOOD_BODY):
        return self.BankEmail._receive_email(
            message_id, subject, body, "alerts@citybank.example")

    def test_parser_extracts_fields(self):
        parsed = self.BankEmail._parse_bank_email(GOOD_SUBJECT, GOOD_BODY)
        self.assertEqual(parsed["amount"], 50000.0)
        self.assertEqual(parsed["transaction_reference"], "TXN-ABC-001")
        self.assertEqual(parsed["bank_name"], "City Bank")
        self.assertEqual(parsed["sender"], "ACME TRADING LTD")
        self.assertTrue(parsed["transaction_date"])

    def test_good_email_creates_pending_incoming(self):
        rec = self._receive("<m1@bank>")
        self.assertEqual(rec.state, "imported")
        inc = rec.incoming_fund_id
        self.assertTrue(inc)
        self.assertEqual(inc.state, "pending")
        self.assertEqual(inc.source, "email")
        self.assertEqual(inc.amount, 50000.0)
        self.assertEqual(inc.fund_account_id, self.account)
        # Pending funds have NOT hit the ledger yet.
        self.assertEqual(self.account.received, 0.0)

    def test_verify_then_confirm_posts_ledger(self):
        rec = self._receive("<m2@bank>")
        inc = rec.incoming_fund_id
        inc.with_user(self.finance_user).action_verify()
        self.assertEqual(inc.state, "draft")
        inc.with_user(self.finance_user).action_confirm()
        self.assertEqual(inc.state, "confirmed")
        self.assertEqual(self.account.received, 50000.0)
        self.assertEqual(self.account.unassigned, 50000.0)

    def test_same_message_id_not_processed_twice(self):
        first = self._receive("<dup@bank>")
        before = self.BankEmail.search_count([])
        second = self._receive("<dup@bank>")
        self.assertEqual(first, second)
        self.assertEqual(self.BankEmail.search_count([]), before)

    def test_duplicate_transaction_reference_flagged(self):
        self._receive("<r1@bank>")
        # Different email, same transaction reference -> flagged, no incoming fund.
        rec = self._receive("<r2@bank>", subject="Re-alert", body=GOOD_BODY)
        self.assertEqual(rec.state, "duplicate")
        self.assertFalse(rec.incoming_fund_id)

    def test_unparseable_email_is_logged_not_dropped(self):
        rec = self._receive("<bad@bank>", subject="Newsletter",
                            body="Thanks for being our customer. No numbers here.")
        self.assertEqual(rec.state, "failed")
        self.assertTrue(rec.error)
        self.assertFalse(rec.incoming_fund_id)

    def test_no_matching_account_waits_for_manual_routing(self):
        body = GOOD_BODY.replace("XXXXXX1234", "XXXXXX9999").replace("City Bank", "Other Bank")
        rec = self._receive("<noacc@bank>", body=body)
        self.assertEqual(rec.state, "parsed")
        self.assertFalse(rec.incoming_fund_id)
        # Finance assigns an account and imports manually.
        rec.fund_account_id = self.account
        rec.action_import()
        self.assertEqual(rec.state, "imported")
        self.assertEqual(rec.incoming_fund_id.state, "pending")
