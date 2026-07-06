# Copyright (c) 2026, alool technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from stockroom.stock.services import events
from stockroom.stock.services.billing import process_after_stock as process_billing
from stockroom.stock.services.transactions.registry import get_handler


def execute(doc) -> None:
	if doc.vouchers:
		frappe.throw(_("Transaction already has linked vouchers"))

	handler = get_handler(doc.transaction_type)
	voucher_refs = handler.execute(doc)

	for ref in voucher_refs:
		doc.append("vouchers", {"voucher_type": ref.voucher_type, "voucher_no": ref.voucher_no})

	doc.flags.ignore_validate_update_after_submit = True
	doc.save(ignore_permissions=True)

	billing_refs = process_billing(doc)
	for ref in billing_refs:
		doc.append("vouchers", {"voucher_type": ref.voucher_type, "voucher_no": ref.voucher_no})
	if billing_refs:
		doc.flags.ignore_validate_update_after_submit = True
		doc.save(ignore_permissions=True)

	stock_entry = next((r.voucher_no for r in voucher_refs if r.voucher_type == "Stock Entry"), None)
	if stock_entry:
		se = frappe.get_doc("Stock Entry", stock_entry)
		payload = events.transaction_payload(doc, se)
		events.emit(events.EVENT_STOCK_VOUCHER_SUBMITTED, payload)

		if doc.transaction_type == "Receive":
			events.emit(events.EVENT_BUY_GOODS_RECEIVED, payload)
		elif doc.transaction_type == "Sell":
			events.emit(events.EVENT_SELL_GOODS_FULFILLED, payload)


def cancel(doc) -> None:
	for row in reversed(list(doc.vouchers or [])):
		if frappe.db.exists(row.voucher_type, row.voucher_no):
			voucher = frappe.get_doc(row.voucher_type, row.voucher_no)
			if voucher.docstatus == 1:
				voucher.cancel()

	if doc.vouchers:
		for row in doc.vouchers:
			if row.voucher_type == "Stock Entry":
				events.emit(
					events.EVENT_STOCK_VOUCHER_CANCELLED,
					{
						"transaction": doc.name,
						"stock_entry": row.voucher_no,
						"company": doc.company,
						"transaction_type": doc.transaction_type,
					},
				)
