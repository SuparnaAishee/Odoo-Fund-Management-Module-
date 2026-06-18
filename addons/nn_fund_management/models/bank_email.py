# -*- coding: utf-8 -*-
"""Bank Email Integration (PDF §12, bonus).

A prototype mail-gateway endpoint: bank transaction-notification emails sent to
the module's alias are parsed into structured fields and turned into incoming
fund records (in *Pending Verification*). The transport is an Odoo incoming-mail
server the admin configures in the UI, so **no bank credentials live in this
source**. Every email is recorded once (deduplicated by Message-ID), duplicate
transaction references are flagged, and unparseable mails are logged rather than
dropped silently.
"""
import logging
import re
from datetime import datetime

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Tolerant patterns for a typical retail-bank credit alert. Required fields are
# the amount and a transaction reference; everything else is best-effort.
_AMOUNT_RE = re.compile(r"(?:BDT|TK|Tk\.?|৳)\s*([\d,]+(?:\.\d{1,2})?)", re.I)
_AMOUNT_LABEL_RE = re.compile(r"amount\s*[:\-]?\s*(?:BDT|TK|Tk\.?|৳)?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
_REF_RE = re.compile(
    r"(?:transaction\s*(?:ref(?:erence)?|id|no)|ref(?:\.|erence)?|txn\s*id|trace(?:\s*(?:no|id))?)"
    r"\s*[:#\-]?\s*([A-Za-z0-9\-/]+)", re.I)
_REF_FALLBACK_RE = re.compile(r"\b(TXN[A-Za-z0-9\-/]+)\b", re.I)
_ACCOUNT_RE = re.compile(
    r"(?:account|a/c)\s*(?:no\.?|number|#)?\s*[:#\-]?\s*([Xx\*]{2,}\d{2,}|\d{6,})", re.I)
_DATE_RE = re.compile(
    r"(?:date|dated|on)\s*[:#\-]?\s*"
    r"([0-3]?\d[-/ ](?:[A-Za-z]{3,9}|\d{1,2})[-/ ]\d{2,4}|\d{4}-\d{2}-\d{2})", re.I)
_BANK_RE = re.compile(r"([A-Z][A-Za-z.&\- ]{1,30}?Bank)\b")
_SENDER_RE = re.compile(
    r"(?:from|sender|beneficiary|remitter)\s*[:#\-]?\s*([A-Za-z0-9 .,&\-/]{2,60})", re.I)

_DATE_FORMATS = (
    "%d-%b-%Y", "%d %b %Y", "%d-%B-%Y", "%d %B %Y",
    "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d",
)


class BankEmail(models.Model):
    _name = "nn.bank.email"
    _description = "Bank Notification Email"
    _inherit = ["mail.thread"]
    _order = "create_date desc, id desc"

    name = fields.Char(string="Reference", required=True, copy=False, readonly=True, default=lambda self: _("New"))
    message_id = fields.Char(string="Email Message-ID", index=True, copy=False, readonly=True)
    subject = fields.Char(string="Subject", readonly=True)
    body_preview = fields.Text(string="Email Body", readonly=True)
    sender_email = fields.Char(string="From", readonly=True)

    # Parsed fields.
    bank_name = fields.Char(string="Bank", readonly=True)
    account_number = fields.Char(string="Account (masked)", readonly=True)
    transaction_reference = fields.Char(string="Transaction Reference", readonly=True)
    transaction_date = fields.Date(string="Transaction Date", readonly=True)
    amount = fields.Monetary(string="Amount", readonly=True)
    sender = fields.Char(string="Sender / Source", readonly=True)
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id, readonly=True)
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True, readonly=True)

    # Finance can pick the target account when auto-matching failed.
    fund_account_id = fields.Many2one("nn.fund.account", string="Fund Account")
    incoming_fund_id = fields.Many2one("nn.incoming.fund", string="Incoming Fund", readonly=True, copy=False)

    state = fields.Selection(
        [
            ("parsed", "Parsed"),
            ("imported", "Imported"),
            ("duplicate", "Duplicate"),
            ("failed", "Parse Failed"),
        ],
        string="Status", default="parsed", required=True, tracking=True,
    )
    error = fields.Text(string="Error / Note", readonly=True)

    _sql_constraints = [
        ("unique_message_id", "UNIQUE(message_id)",
         "This bank email (Message-ID) has already been processed."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("nn.bank.email") or _("New")
        return super().create(vals_list)

    # ---- parsing -------------------------------------------------------- #
    @api.model
    def _parse_bank_email(self, subject, body):
        """Extract structured fields from a bank alert. Raises ``ValueError`` if
        the two required fields (amount, transaction reference) are absent."""
        text = "%s\n%s" % (subject or "", body or "")

        amount_m = _AMOUNT_LABEL_RE.search(text) or _AMOUNT_RE.search(text)
        ref_m = _REF_RE.search(text) or _REF_FALLBACK_RE.search(text)
        missing = []
        if not amount_m:
            missing.append("amount")
        if not ref_m:
            missing.append("transaction reference")
        if missing:
            raise ValueError(_("Could not parse %s from the email.", ", ".join(missing)))

        date_m = _DATE_RE.search(text)
        bank_m = _BANK_RE.search(text)
        acct_m = _ACCOUNT_RE.search(text)
        sender_m = _SENDER_RE.search(text)
        return {
            "amount": float(amount_m.group(1).replace(",", "")),
            "transaction_reference": ref_m.group(1).strip(),
            "transaction_date": self._parse_date(date_m.group(1)) if date_m else False,
            "bank_name": bank_m.group(1).strip() if bank_m else False,
            "account_number": acct_m.group(1).strip() if acct_m else False,
            "sender": sender_m.group(1).strip(" .,-") if sender_m else False,
        }

    @api.model
    def _parse_date(self, raw):
        raw = (raw or "").strip()
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
        return False

    # ---- ingestion ------------------------------------------------------ #
    @api.model
    def _receive_email(self, message_id, subject, body, sender_email=False, company=None):
        """Single entry point for processing one bank email. Idempotent: a
        Message-ID already seen returns the existing record without re-importing.
        Returns the ``nn.bank.email`` record."""
        company = company or self.env.company
        if message_id:
            existing = self.sudo().search([("message_id", "=", message_id)], limit=1)
            if existing:
                _logger.info("Bank email %s already processed; skipping.", message_id)
                return existing

        vals = {
            "message_id": message_id,
            "subject": subject or "",
            "body_preview": (body or "")[:4000],
            "sender_email": sender_email or False,
            "company_id": company.id,
            "currency_id": company.currency_id.id,
        }
        try:
            parsed = self._parse_bank_email(subject, body)
        except ValueError as err:
            vals.update({"state": "failed", "error": str(err)})
            rec = self.sudo().create(vals)
            _logger.warning("Bank email parse failed (%s): %s", message_id, err)
            return rec

        vals.update(parsed)
        vals["state"] = "parsed"
        rec = self.sudo().create(vals)
        rec._try_import()
        return rec

    def _guess_account(self):
        """Auto-route to a fund account by account-number tail or bank name."""
        self.ensure_one()
        Account = self.env["nn.fund.account"].sudo()
        if self.account_number:
            digits = re.sub(r"\D", "", self.account_number)
            for acc in Account.search([("account_ref", "!=", False)]):
                key = re.sub(r"\D", "", acc.account_ref or "")
                if key and digits.endswith(key):
                    return acc
        if self.bank_name:
            acc = Account.search([("bank_name", "=", self.bank_name)], limit=1)
            if acc:
                return acc
        return Account.browse()

    def _try_import(self):
        """Create the pending incoming-fund record, unless the transaction
        reference is a duplicate or no target account can be determined."""
        self.ensure_one()
        Incoming = self.env["nn.incoming.fund"].sudo()

        if self.transaction_reference:
            dup = Incoming.search(
                [("transaction_reference", "=", self.transaction_reference)], limit=1)
            if dup:
                self.write({
                    "state": "duplicate",
                    "error": _("Transaction reference %(ref)s already exists on %(doc)s.",
                               ref=self.transaction_reference, doc=dup.name),
                })
                _logger.info("Bank email %s is a duplicate of %s.", self.name, dup.name)
                return

        account = self.fund_account_id or self._guess_account()
        if not account:
            # Parsed fine, but finance must pick an account before import.
            self.error = _("No matching fund account; assign one and import manually.")
            return

        incoming = Incoming.create({
            "fund_account_id": account.id,
            "amount": self.amount,
            "date": self.transaction_date or fields.Date.context_today(self),
            "transaction_reference": self.transaction_reference,
            "sender": self.sender or self.sender_email,
            "description": self.subject,
            "source": "email",
            "bank_email_id": self.id,
            "email_message_id": self.message_id,
            "state": "pending",
        })
        self.write({
            "state": "imported",
            "fund_account_id": account.id,
            "incoming_fund_id": incoming.id,
        })

    # ---- UI actions ----------------------------------------------------- #
    def action_import(self):
        """Manually create the incoming fund after finance assigns an account."""
        for rec in self:
            if rec.state not in ("parsed",) or rec.incoming_fund_id:
                raise UserError(_("Only a parsed, not-yet-imported email can be imported."))
            if not rec.fund_account_id:
                raise UserError(_("Select a fund account first."))
            rec._try_import()
        return True

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """Mail-gateway hook: an email hitting the alias lands here. We parse it
        into a bank-email record (and a pending incoming fund) instead of a bare
        thread, and dedupe on Message-ID."""
        body = tools.html2plaintext(msg_dict.get("body") or "")
        return self._receive_email(
            msg_dict.get("message_id"),
            msg_dict.get("subject"),
            body,
            msg_dict.get("email_from") or msg_dict.get("from"),
        )

    def action_ingest_sample(self):
        """Demo helper: synthesise one realistic bank alert and process it, so
        the feature can be shown end-to-end without a live mail server."""
        n = self.search_count([]) + 1
        message_id = "<demo-bank-%05d@bank.example>" % n
        ref = "TXN%05d" % n
        subject = "Transaction Alert: BDT 50,000.00 Credited"
        body = (
            "Dear Customer,\n"
            "Your account XXXXXX%04d with City Bank has been credited.\n"
            "Amount: BDT 50,000.00\n"
            "Transaction Ref: %s\n"
            "Date: 19-Jun-2026\n"
            "From: ACME TRADING LTD\n"
            "Thank you for banking with us." % (1000 + n, ref)
        )
        self._receive_email(message_id, subject, body, "alerts@citybank.example")
        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }
