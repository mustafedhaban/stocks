# Copyright (c) 2026, alool technologies and contributors
# For license information, please see license.txt

from stockroom.stock.services.transactions.base import TransactionHandler, VoucherRef, _line_warehouse, build_stock_entry


class QuickSellHandler(TransactionHandler):
	transaction_type = "Sell"

	def execute(self, doc):
		def add_line(se, txn, row):
			warehouse = _line_warehouse(txn, row, "default_warehouse")
			se.append(
				"items",
				{
					"item_code": row.item_code,
					"qty": row.qty,
					"s_warehouse": warehouse,
				},
			)

		stock_entry = build_stock_entry(doc, "Material Issue", add_line)
		return [VoucherRef("Stock Entry", stock_entry.name)]
