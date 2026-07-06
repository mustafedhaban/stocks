# Copyright (c) 2026, alool technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt

from stockroom.stock.services.transactions.base import TransactionHandler, VoucherRef, _line_warehouse, build_stock_entry
from stockroom.stock.stock_utils import get_stock_balance


class QuickAdjustHandler(TransactionHandler):
	transaction_type = "Adjust"

	def execute(self, doc):
		# qty on lines = counted/on-hand target; delta drives movement
		def add_line(se, txn, row):
			warehouse = _line_warehouse(txn, row, "default_warehouse")
			current = get_stock_balance(row.item_code, warehouse, txn.posting_date, txn.posting_time)
			delta = flt(row.qty) - flt(current)
			if not delta:
				return

			line = {"item_code": row.item_code, "qty": abs(delta)}
			if delta > 0:
				line["t_warehouse"] = warehouse
			else:
				line["s_warehouse"] = warehouse
			se.append("items", line)

		stock_entry = build_stock_entry(doc, "Stock Reconciliation", add_line)
		return [VoucherRef("Stock Entry", stock_entry.name)]
