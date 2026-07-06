# Copyright (c) 2026, alool technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from stockroom.stock.stock_utils import cancel_stock_ledger_entries, make_stock_ledger_entries, _validate_warehouse


class StockEntry(Document):
	def validate(self):
		self.validate_items()

	def validate_items(self):
		if not self.items:
			frappe.throw(_("Please add at least one item row"))

		for row in self.items:
			if flt(row.qty) <= 0:
				frappe.throw(_("Row {0}: Qty must be greater than 0").format(row.idx))

			item = frappe.get_cached_value(
				"Item", row.item_code, ["is_stock_item", "disabled"], as_dict=True
			)
			if not item or not item.is_stock_item:
				frappe.throw(_("Row {0}: {1} is not a stock item").format(row.idx, row.item_code))
			if item.disabled:
				frappe.throw(_("Row {0}: {1} is disabled").format(row.idx, row.item_code))

			if self.stock_entry_type == "Material Receipt" and not row.t_warehouse:
				frappe.throw(_("Row {0}: Target Warehouse is required for Material Receipt").format(row.idx))
			elif self.stock_entry_type == "Material Issue" and not row.s_warehouse:
				frappe.throw(_("Row {0}: Source Warehouse is required for Material Issue").format(row.idx))
			elif self.stock_entry_type == "Material Transfer":
				if not row.s_warehouse or not row.t_warehouse:
					frappe.throw(_("Row {0}: Source and Target Warehouse are required for Material Transfer").format(row.idx))
				if row.s_warehouse == row.t_warehouse:
					frappe.throw(_("Row {0}: Source and Target Warehouse cannot be the same").format(row.idx))
			elif self.stock_entry_type == "Stock Reconciliation":
				if not row.t_warehouse and not row.s_warehouse:
					frappe.throw(_("Row {0}: Warehouse is required for Stock Reconciliation").format(row.idx))

			for wh in (row.s_warehouse, row.t_warehouse):
				if wh:
					_validate_warehouse(wh)

	def on_submit(self):
		make_stock_ledger_entries(self)

	def on_cancel(self):
		cancel_stock_ledger_entries(self.doctype, self.name)
