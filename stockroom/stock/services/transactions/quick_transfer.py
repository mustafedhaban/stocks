# Copyright (c) 2026, alool technologies and contributors
# For license information, please see license.txt

from stockroom.stock.services.transactions.base import TransactionHandler, VoucherRef, build_stock_entry


class QuickTransferHandler(TransactionHandler):
	transaction_type = "Transfer"

	def execute(self, doc):
		def add_line(se, txn, row):
			s_wh = row.s_warehouse or txn.source_warehouse
			t_wh = row.t_warehouse or txn.target_warehouse
			se.append(
				"items",
				{
					"item_code": row.item_code,
					"qty": row.qty,
					"s_warehouse": s_wh,
					"t_warehouse": t_wh,
				},
			)

		stock_entry = build_stock_entry(doc, "Material Transfer", add_line)
		return [VoucherRef("Stock Entry", stock_entry.name)]
