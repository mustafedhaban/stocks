# Copyright (c) 2026, alool technologies and contributors

from __future__ import annotations

import frappe
from frappe.utils import cint, flt

from stockroom.stock.services.parties import get_or_create_customer, get_or_create_supplier
from stockroom.stock.services.transactions.base import VoucherRef


def process_after_stock(doc) -> list[VoucherRef]:
	refs: list[VoucherRef] = []

	if doc.transaction_type == "Receive":
		if doc.purchase_order:
			from stockroom.buy.doctype.purchase_order.purchase_order import update_received_qty

			update_received_qty(
				doc.purchase_order,
				[{"item_code": row.item_code, "qty": row.qty} for row in doc.items],
			)
		refs.extend(_create_purchase_invoice(doc))
	elif doc.transaction_type == "Sell":
		if doc.sales_order:
			from stockroom.sell.doctype.sales_order.sales_order import update_delivered_qty

			update_delivered_qty(
				doc.sales_order,
				[{"item_code": row.item_code, "qty": row.qty} for row in doc.items],
			)
		refs.extend(_create_sales_invoice(doc))

	return refs


def _create_purchase_invoice(doc) -> list[VoucherRef]:
	if not cint(frappe.db.get_single_value("Stock Settings", "auto_create_purchase_invoice")):
		return []

	if not doc.party_name and not doc.supplier:
		return []

	supplier = doc.supplier or get_or_create_supplier(doc.party_name, doc.company)
	items = [
		{
			"item_code": row.item_code,
			"qty": row.qty,
			"rate": row.rate,
			"warehouse": row.warehouse or doc.default_warehouse,
		}
		for row in doc.items
	]
	if not any(flt(i["rate"]) for i in items):
		return []

	pi = frappe.get_doc(
		{
			"doctype": "Purchase Invoice",
			"supplier": supplier,
			"company": doc.company,
			"posting_date": doc.posting_date,
			"purchase_order": doc.purchase_order,
			"stock_transaction": doc.name,
			"items": items,
			"remarks": doc.remarks,
		}
	)
	pi.insert(ignore_permissions=True)

	if cint(frappe.db.get_single_value("Stock Settings", "auto_submit_invoices")):
		pi.submit()

	return [VoucherRef("Purchase Invoice", pi.name)]


def _create_sales_invoice(doc) -> list[VoucherRef]:
	if not cint(frappe.db.get_single_value("Stock Settings", "auto_create_sales_invoice")):
		return []

	if not doc.party_name and not doc.customer:
		return []

	customer = doc.customer or get_or_create_customer(doc.party_name, doc.company)
	items = [
		{
			"item_code": row.item_code,
			"qty": row.qty,
			"rate": row.rate,
			"warehouse": row.warehouse or doc.default_warehouse,
		}
		for row in doc.items
	]
	if not any(flt(i["rate"]) for i in items):
		return []

	si = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"customer": customer,
			"company": doc.company,
			"posting_date": doc.posting_date,
			"sales_order": doc.sales_order,
			"stock_transaction": doc.name,
			"items": items,
			"remarks": doc.remarks,
		}
	)
	si.insert(ignore_permissions=True)

	if cint(frappe.db.get_single_value("Stock Settings", "auto_submit_invoices")):
		si.submit()

	return [VoucherRef("Sales Invoice", si.name)]
