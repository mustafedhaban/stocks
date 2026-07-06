# Copyright (c) 2026, alool technologies and contributors
# For license information, please see license.txt

from __future__ import annotations

from dataclasses import dataclass

import frappe
from frappe.model.document import Document


@dataclass
class VoucherRef:
	voucher_type: str
	voucher_no: str


class TransactionHandler:
	transaction_type: str

	def execute(self, doc: Document) -> list[VoucherRef]:
		raise NotImplementedError

	def cancel(self, doc: Document) -> None:
		for row in doc.vouchers:
			if frappe.db.exists(row.voucher_type, row.voucher_no):
				voucher = frappe.get_doc(row.voucher_type, row.voucher_no)
				if voucher.docstatus == 1:
					voucher.cancel()


def _line_warehouse(doc, row, default_field: str) -> str:
	return row.warehouse or doc.get(default_field) or ""


def build_stock_entry(doc, stock_entry_type: str, line_builder) -> Document:
	"""Create a draft Stock Entry from orchestrator doc."""
	se = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": stock_entry_type,
			"company": doc.company,
			"posting_date": doc.posting_date,
			"posting_time": doc.posting_time,
			"remarks": doc.remarks or f"From {doc.name}",
			"items": [],
		}
	)

	for row in doc.items:
		line_builder(se, doc, row)

	if not se.items:
		from frappe import _

		frappe.throw(_("No stock movements to process"))

	se.insert()
	se.submit()
	return se
