# Copyright (c) 2026, alool technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from stockroom.stock.services.transactions.orchestrator import cancel as orchestrator_cancel
from stockroom.stock.services.transactions.orchestrator import execute as orchestrator_execute
from stockroom.stock.stock_utils import _validate_warehouse


class StockTransaction(Document):
	def validate(self):
		self.validate_items()
		for row in self.items:
			row.amount = flt(row.qty) * flt(row.rate or 0)
		self.set_totals()

	def validate_items(self):
		if not self.items:
			frappe.throw(_("Add at least one item"))

		if self.transaction_type in ("Receive", "Sell", "Adjust") and not self.default_warehouse:
			if not any(row.warehouse for row in self.items):
				frappe.throw(_("Set a default warehouse or specify warehouse on each line"))

		if self.transaction_type == "Transfer":
			if not self.source_warehouse or not self.target_warehouse:
				frappe.throw(_("From and To warehouse are required for Transfer"))
			if self.source_warehouse == self.target_warehouse:
				frappe.throw(_("From and To warehouse cannot be the same"))

		for row in self.items:
			if flt(row.qty) <= 0 and self.transaction_type != "Adjust":
				frappe.throw(_("Row {0}: Qty must be greater than 0").format(row.idx))
			if self.transaction_type == "Adjust" and flt(row.qty) < 0:
				frappe.throw(_("Row {0}: Adjust qty is the counted balance and cannot be negative").format(row.idx))
			for wh in (row.warehouse, self.default_warehouse, self.source_warehouse, self.target_warehouse):
				if wh:
					_validate_warehouse(wh)

	def set_totals(self):
		self.total_qty = sum(flt(row.qty) for row in self.items)
		self.total_amount = sum(flt(row.amount) for row in self.items)

	def on_submit(self):
		orchestrator_execute(self)

	def on_cancel(self):
		orchestrator_cancel(self)
