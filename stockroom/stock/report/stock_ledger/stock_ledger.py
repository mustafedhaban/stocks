# Copyright (c) 2026, alool technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def validate_filters(filters):
	if not filters.get("company"):
		frappe.throw(_("Company is required"))


def get_columns():
	return [
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 120,
		},
		{
			"label": _("Warehouse"),
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 140,
		},
		{
			"label": _("Qty Change"),
			"fieldname": "actual_qty",
			"fieldtype": "Float",
			"width": 100,
		},
		{
			"label": _("Balance Qty"),
			"fieldname": "qty_after_transaction",
			"fieldtype": "Float",
			"width": 110,
		},
		{
			"label": _("Voucher Type"),
			"fieldname": "voucher_type",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Voucher No"),
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 150,
		},
	]


def get_data(filters):
	conditions = ["sle.is_cancelled = 0", "sle.company = %(company)s"]
	values = {"company": filters.company}

	if filters.get("warehouse"):
		conditions.append("sle.warehouse = %(warehouse)s")
		values["warehouse"] = filters.warehouse

	if filters.get("item_code"):
		conditions.append("sle.item_code = %(item_code)s")
		values["item_code"] = filters.item_code

	if filters.get("from_date"):
		conditions.append("sle.posting_date >= %(from_date)s")
		values["from_date"] = filters.from_date

	if filters.get("to_date"):
		conditions.append("sle.posting_date <= %(to_date)s")
		values["to_date"] = filters.to_date

	return frappe.db.sql(
		f"""
		SELECT
			sle.posting_date,
			sle.item_code,
			sle.warehouse,
			sle.actual_qty,
			sle.qty_after_transaction,
			sle.voucher_type,
			sle.voucher_no
		FROM `tabStock Ledger Entry` sle
		WHERE {" AND ".join(conditions)}
		ORDER BY sle.posting_date, sle.posting_time, sle.creation
		""",
		values,
		as_dict=True,
	)
