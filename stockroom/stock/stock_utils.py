# Copyright (c) 2026, alool technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, nowtime, today


def make_stock_ledger_entries(stock_entry):
	entries = []
	for row in stock_entry.items:
		if stock_entry.stock_entry_type == "Material Receipt":
			entries.append(_entry(stock_entry, row, row.t_warehouse, flt(row.qty)))
		elif stock_entry.stock_entry_type == "Material Issue":
			entries.append(_entry(stock_entry, row, row.s_warehouse, -flt(row.qty)))
		elif stock_entry.stock_entry_type == "Material Transfer":
			entries.append(_entry(stock_entry, row, row.s_warehouse, -flt(row.qty)))
			entries.append(_entry(stock_entry, row, row.t_warehouse, flt(row.qty)))
		elif stock_entry.stock_entry_type == "Stock Reconciliation":
			if row.s_warehouse:
				entries.append(_entry(stock_entry, row, row.s_warehouse, -flt(row.qty)))
			elif row.t_warehouse:
				entries.append(_entry(stock_entry, row, row.t_warehouse, flt(row.qty)))

	make_sl_entries(entries)


def _entry(stock_entry, row, warehouse, actual_qty):
	return {
		"item_code": row.item_code,
		"warehouse": warehouse,
		"posting_date": stock_entry.posting_date,
		"posting_time": stock_entry.posting_time or nowtime(),
		"voucher_type": stock_entry.doctype,
		"voucher_no": stock_entry.name,
		"voucher_detail_no": row.name,
		"company": stock_entry.company,
		"actual_qty": actual_qty,
	}


def make_sl_entries(entries, allow_negative_stock=None):
	if allow_negative_stock is None:
		allow_negative_stock = cint(frappe.db.get_single_value("Stock Settings", "allow_negative_stock"))

	for entry in entries:
		_validate_warehouse(entry["warehouse"])
		previous_qty = get_stock_balance(
			entry["item_code"],
			entry["warehouse"],
			entry["posting_date"],
			entry["posting_time"],
		)
		qty_after = flt(previous_qty) + flt(entry["actual_qty"])

		if qty_after < 0 and not allow_negative_stock:
			frappe.throw(
				_("Insufficient stock for {0} in {1}. Available: {2}").format(
					entry["item_code"], entry["warehouse"], previous_qty
				)
			)

		sle = frappe.get_doc(
			{
				"doctype": "Stock Ledger Entry",
				"item_code": entry["item_code"],
				"warehouse": entry["warehouse"],
				"posting_date": entry["posting_date"],
				"posting_time": entry["posting_time"],
				"voucher_type": entry["voucher_type"],
				"voucher_no": entry["voucher_no"],
				"voucher_detail_no": entry.get("voucher_detail_no"),
				"company": entry["company"],
				"actual_qty": entry["actual_qty"],
				"qty_after_transaction": qty_after,
			}
		)
		sle.flags.ignore_permissions = True
		sle.insert()


def cancel_stock_ledger_entries(voucher_type, voucher_no):
	sle_names = frappe.get_all(
		"Stock Ledger Entry",
		filters={"voucher_type": voucher_type, "voucher_no": voucher_no, "is_cancelled": 0},
		pluck="name",
	)
	if not sle_names:
		return

	for sle_name in sle_names:
		sle = frappe.get_doc("Stock Ledger Entry", sle_name)
		if _has_later_entries(sle):
			frappe.throw(
				_("Cannot cancel because later stock transactions exist for {0} in {1}").format(
					sle.item_code, sle.warehouse
				)
			)

	for sle_name in sle_names:
		frappe.db.set_value("Stock Ledger Entry", sle_name, "is_cancelled", 1)


def get_stock_balance(item_code, warehouse, posting_date=None, posting_time=None):
	if not posting_date:
		posting_date = today()
	if not posting_time:
		posting_time = nowtime()

	posting_datetime = get_datetime(f"{posting_date} {posting_time}")

	last_sle = frappe.db.sql(
		"""
		SELECT qty_after_transaction
		FROM `tabStock Ledger Entry`
		WHERE item_code = %s
			AND warehouse = %s
			AND is_cancelled = 0
			AND (
				posting_date < %s
				OR (posting_date = %s AND posting_time <= %s)
			)
		ORDER BY posting_date DESC, posting_time DESC, creation DESC
		LIMIT 1
		""",
		(item_code, warehouse, posting_date, posting_date, posting_time),
	)

	if last_sle:
		return flt(last_sle[0][0])

	return 0.0


def _has_later_entries(sle):
	return frappe.db.exists(
		"Stock Ledger Entry",
		{
			"item_code": sle.item_code,
			"warehouse": sle.warehouse,
			"is_cancelled": 0,
			"name": ("!=", sle.name),
			"posting_date": (">=", sle.posting_date),
		},
	)


def _validate_warehouse(warehouse):
	if frappe.get_cached_value("Warehouse", warehouse, "is_group"):
		frappe.throw(_("Stock cannot be stored in group warehouse {0}").format(warehouse))

	if frappe.get_cached_value("Warehouse", warehouse, "disabled"):
		frappe.throw(_("Warehouse {0} is disabled").format(warehouse))
