# Copyright (c) 2026, alool technologies and contributors
"""
End-to-end Standard Buy flow: PO → partial Receive → PO status + Purchase Invoice.

Run:
  cd /path/to/demoenv
  bench --site stock execute stockroom.stock.scripts.e2e_standard_buy_flow.run --kwargs "{'cleanup': True}"
"""

from __future__ import annotations

import frappe
from frappe.utils import flt

from stockroom.stock.scripts.e2e_receive_flow import (
	COMPANY_NAME,
	ITEM_CODE,
	RATE,
	SUPPLIER_NAME,
	WAREHOUSE_NAME,
	_cleanup as cleanup_e2e,
	_ensure_company,
	_ensure_masters,
	_ensure_posting_profile,
	_ensure_stock_settings,
	_voucher,
)
from stockroom.stock.services.parties import get_or_create_supplier
from stockroom.stock.stock_utils import get_stock_balance

PO_QTY = 20
RECEIVE_QTY = 10
EXPECTED_PI_AMOUNT = RECEIVE_QTY * RATE


def run(cleanup: bool = False) -> dict:
	frappe.set_user("Administrator")
	if cleanup:
		cleanup_e2e()

	report = {"steps": [], "checks": {}, "pass": False}

	try:
		company = _ensure_company()
		report["steps"].append(f"Company ready: {company}")

		_ensure_posting_profile(company)
		_ensure_masters(company)
		_ensure_stock_settings()
		frappe.db.set_single_value("Stock Settings", "default_workflow_mode", "Standard")
		supplier = get_or_create_supplier(SUPPLIER_NAME, company)
		report["steps"].append(f"Supplier ready: {supplier}")

		po = _submit_po(company, supplier)
		report["purchase_order"] = po.name
		report["steps"].append(f"Submitted Purchase Order: {po.name} ({PO_QTY} × {ITEM_CODE})")

		balance_before = get_stock_balance(ITEM_CODE, WAREHOUSE_NAME)
		report["balance_before"] = balance_before

		txn = _submit_partial_receive(company, po.name)
		report["transaction"] = txn.name
		report["steps"].append(f"Partial receive: {txn.name} ({RECEIVE_QTY} units)")

		report["checks"] = _verify(po.name, txn, balance_before)
		report["pass"] = all(report["checks"].values())
		frappe.db.commit()
	except Exception as e:
		frappe.db.rollback()
		report["error"] = str(e)
		raise
	finally:
		_print_report(report)

	return report


def _submit_po(company: str, supplier: str):
	po = frappe.get_doc(
		{
			"doctype": "Purchase Order",
			"supplier": supplier,
			"company": company,
			"items": [
				{
					"item_code": ITEM_CODE,
					"qty": PO_QTY,
					"rate": RATE,
					"warehouse": WAREHOUSE_NAME,
				}
			],
		}
	)
	po.insert(ignore_permissions=True)
	po.submit()
	return po


def _submit_partial_receive(company: str, purchase_order: str):
	txn = frappe.get_doc(
		{
			"doctype": "Stock Transaction",
			"transaction_type": "Receive",
			"company": company,
			"party_name": SUPPLIER_NAME,
			"purchase_order": purchase_order,
			"default_warehouse": WAREHOUSE_NAME,
			"items": [{"item_code": ITEM_CODE, "qty": RECEIVE_QTY, "rate": RATE}],
		}
	)
	txn.insert(ignore_permissions=True)
	txn.submit()
	return txn


def _verify(purchase_order: str, txn, balance_before: float) -> dict:
	po = frappe.get_doc("Purchase Order", purchase_order)
	po_line = po.items[0]

	stock_entry = _voucher(txn, "Stock Entry")
	purchase_invoice = _voucher(txn, "Purchase Invoice")
	balance_after = get_stock_balance(ITEM_CODE, WAREHOUSE_NAME)

	stock_gl = frappe.db.count(
		"GL Entry",
		{
			"voucher_type": "Stock Entry",
			"voucher_no": stock_entry,
			"is_cancelled": 0,
			"remarks": ["like", f"%{txn.name}%"],
		},
	)

	pi_gl = 0
	pi_total = 0
	pi_po_link = None
	if purchase_invoice:
		pi_gl = frappe.db.count(
			"GL Entry",
			{"voucher_type": "Purchase Invoice", "voucher_no": purchase_invoice, "is_cancelled": 0},
		)
		pi_total = frappe.db.get_value("Purchase Invoice", purchase_invoice, "grand_total")
		pi_po_link = frappe.db.get_value("Purchase Invoice", purchase_invoice, "purchase_order")

	gl_debit_stock = frappe.db.sql(
		"""
		SELECT SUM(debit) FROM `tabGL Entry`
		WHERE voucher_type = 'Stock Entry' AND voucher_no = %s AND is_cancelled = 0
			AND remarks LIKE %s
		""",
		(stock_entry, f"%{txn.name}%"),
	)[0][0] or 0

	return {
		"po_status_partial": po.status == "Partially Received",
		"po_received_qty": flt(po_line.received_qty) == RECEIVE_QTY,
		"po_remaining_qty": flt(po_line.qty) - flt(po_line.received_qty) == PO_QTY - RECEIVE_QTY,
		"txn_linked_to_po": txn.purchase_order == purchase_order,
		"stock_entry_created": bool(stock_entry),
		"sle_balance_increased": flt(balance_after) == flt(balance_before) + RECEIVE_QTY,
		"stock_gl_entries": stock_gl >= 2,
		"stock_gl_amount": flt(gl_debit_stock) == EXPECTED_PI_AMOUNT,
		"purchase_invoice_created": bool(purchase_invoice),
		"purchase_invoice_linked_to_po": pi_po_link == purchase_order,
		"purchase_invoice_total": flt(pi_total) == EXPECTED_PI_AMOUNT,
		"purchase_invoice_gl": pi_gl >= 2 if purchase_invoice else False,
	}


def _print_report(report: dict):
	print("\n" + "=" * 60)
	print("STOCKROOM E2E — STANDARD BUY (PO → RECEIVE)")
	print("=" * 60)
	for step in report.get("steps", []):
		print(f"  ✓ {step}")
	if report.get("purchase_order"):
		print(f"\nPurchase Order: {report['purchase_order']}")
	if report.get("transaction"):
		print(f"Stock Transaction: {report['transaction']}")
	print("\nChecks:")
	for check, ok in report.get("checks", {}).items():
		print(f"  {'PASS' if ok else 'FAIL'} — {check}")
	print(f"\nOverall: {'PASS' if report.get('pass') else 'FAIL'}")
	if report.get("error"):
		print(f"Error: {report['error']}")
	print("=" * 60 + "\n")
