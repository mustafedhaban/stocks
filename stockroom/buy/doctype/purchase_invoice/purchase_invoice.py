# Copyright (c) 2026, alool technologies and contributors

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from manager.accounts.services.gl_posting import (
	build_purchase_invoice_gl,
	cancel_gl_entries,
	get_posting_profile,
	make_gl_entries,
)
from manager.accounts.services.invoice_payment import init_invoice_payment_fields


class PurchaseInvoice(Document):
	def validate(self):
		if not self.items:
			frappe.throw(_("Add at least one item"))
		for row in self.items:
			row.amount = flt(row.qty) * flt(row.rate or 0)
		self.grand_total = sum(flt(r.amount) for r in self.items)

	def on_submit(self):
		profile = get_posting_profile(self.company)
		entries = build_purchase_invoice_gl(self, profile)
		make_gl_entries(entries, self.company)
		init_invoice_payment_fields(self)

	def on_cancel(self):
		cancel_gl_entries(self.doctype, self.name)
