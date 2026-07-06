# Copyright (c) 2026, alool technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import parse_json


@frappe.whitelist()
def create_transaction(data):
	"""API entry: create and submit a Stock Transaction in one call."""
	data = parse_json(data) if isinstance(data, str) else frappe._dict(data or {})

	doc = frappe.get_doc(
		{
			"doctype": "Stock Transaction",
			"transaction_type": data.get("transaction_type"),
			"company": data.get("company"),
			"party_name": data.get("party_name"),
			"default_warehouse": data.get("default_warehouse"),
			"source_warehouse": data.get("source_warehouse"),
			"target_warehouse": data.get("target_warehouse"),
			"posting_date": data.get("posting_date"),
			"posting_time": data.get("posting_time"),
			"remarks": data.get("remarks"),
			"items": data.get("items") or [],
		}
	)
	doc.insert()
	doc.submit()

	return {
		"name": doc.name,
		"vouchers": [{"voucher_type": v.voucher_type, "voucher_no": v.voucher_no} for v in doc.vouchers],
	}


@frappe.whitelist()
def cancel_transaction(name):
	doc = frappe.get_doc("Stock Transaction", name)
	if doc.docstatus != 1:
		frappe.throw(_("Only submitted transactions can be cancelled"))
	doc.cancel()
	return {"name": doc.name, "status": "cancelled"}
