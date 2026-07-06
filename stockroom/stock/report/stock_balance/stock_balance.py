# Copyright (c) 2026, alool technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


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
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 140,
		},
		{
			"label": _("Item Name"),
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _("Warehouse"),
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 160,
		},
		{
			"label": _("Balance Qty"),
			"fieldname": "balance_qty",
			"fieldtype": "Float",
			"width": 120,
		},
		{
			"label": _("UOM"),
			"fieldname": "stock_uom",
			"fieldtype": "Link",
			"options": "UOM",
			"width": 100,
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

	if filters.get("to_date"):
		conditions.append("sle.posting_date <= %(to_date)s")
		values["to_date"] = filters.to_date

	rows = frappe.db.sql(
		f"""
		SELECT
			sle.item_code,
			i.item_name,
			sle.warehouse,
			sle.qty_after_transaction,
			sle.posting_date,
			sle.posting_time,
			sle.creation,
			i.stock_uom
		FROM `tabStock Ledger Entry` sle
		INNER JOIN `tabItem` i ON i.name = sle.item_code
		WHERE {" AND ".join(conditions)}
		ORDER BY sle.posting_date DESC, sle.posting_time DESC, sle.creation DESC
		""",
		values,
		as_dict=True,
	)

	seen = set()
	data = []
	for row in rows:
		key = (row.item_code, row.warehouse)
		if key in seen:
			continue
		seen.add(key)
		data.append(
			{
				"item_code": row.item_code,
				"item_name": row.item_name,
				"warehouse": row.warehouse,
				"balance_qty": flt(row.qty_after_transaction),
				"stock_uom": row.stock_uom,
			}
		)

	return sorted(data, key=lambda d: (d["item_code"], d["warehouse"]))
