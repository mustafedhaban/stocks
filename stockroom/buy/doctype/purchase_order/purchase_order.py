# Copyright (c) 2026, alool technologies and contributors

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class PurchaseOrder(Document):
	def validate(self):
		if not self.items:
			frappe.throw(_("Add at least one item"))
		for row in self.items:
			row.amount = flt(row.qty) * flt(row.rate or 0)
		self.total_qty = sum(flt(r.qty) for r in self.items)
		self.grand_total = sum(flt(r.amount) for r in self.items)
		self.update_status()

	def on_submit(self):
		self.db_set("status", "Submitted")

	def on_cancel(self):
		self.db_set("status", "Cancelled")

	def update_status(self):
		if self.docstatus == 0:
			self.status = "Draft"
			return
		if self.docstatus == 2:
			self.status = "Cancelled"
			return
		total = sum(flt(r.qty) for r in self.items)
		received = sum(flt(r.received_qty) for r in self.items)
		if received <= 0:
			self.status = "Submitted"
		elif received >= total:
			self.status = "Completed"
		else:
			self.status = "Partially Received"


def update_received_qty(purchase_order: str, items: list[dict]):
	if not purchase_order or not frappe.db.exists("Purchase Order", purchase_order):
		return

	po = frappe.get_doc("Purchase Order", purchase_order)
	item_map = {row.item_code: row for row in po.items}

	for line in items:
		row = item_map.get(line.get("item_code"))
		if row:
			row.received_qty = flt(row.received_qty) + flt(line.get("qty"))

	po.update_status()
	po.flags.ignore_validate_update_after_submit = True
	po.save(ignore_permissions=True)
