# Copyright (c) 2026, alool technologies and contributors
"""
End-to-end Standard Sell flow: SO → partial Sell → SO status + Sales Invoice.

Run:
  cd /path/to/demoenv
  bench --site stock execute stockroom.stock.scripts.e2e_standard_sell_flow.run --kwargs "{'cleanup': True}"
"""

from __future__ import annotations

import frappe
from frappe.utils import flt

from stockroom.stock.scripts.e2e_receive_flow import (
	COMPANY_NAME,
	ITEM_CODE,
	RATE,
	WAREHOUSE_NAME,
	_cleanup as cleanup_e2e,
	_ensure_company,
	_ensure_masters,
	_ensure_posting_profile,
	_ensure_stock_settings,
	_submit_receive,
	_voucher,
)
from stockroom.stock.services.parties import get_or_create_customer
from stockroom.stock.stock_utils import get_stock_balance

CUSTOMER_NAME = "_E2E Retail"
SO_QTY = 20
SELL_QTY = 10
EXPECTED_SI_AMOUNT = SELL_QTY * RATE


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

		customer = get_or_create_customer(CUSTOMER_NAME, company)
		report["steps"].append(f"Customer ready: {customer}")

		_ensure_stock_on_hand(company, report)

		so = _submit_so(company, customer)
		report["sales_order"] = so.name
		report["steps"].append(f"Submitted Sales Order: {so.name} ({SO_QTY} × {ITEM_CODE})")

		balance_before = get_stock_balance(ITEM_CODE, WAREHOUSE_NAME)
		report["balance_before"] = balance_before

		txn = _submit_partial_sell(company, so.name)
		report["transaction"] = txn.name
		report["steps"].append(f"Partial sell: {txn.name} ({SELL_QTY} units)")

		report["checks"] = _verify(so.name, txn, balance_before)
		report["pass"] = all(report["checks"].values())
		frappe.db.commit()
	except Exception as e:
		frappe.db.rollback()
		report["error"] = str(e)
		raise
	finally:
		_print_report(report)

	return report


def _ensure_stock_on_hand(company: str, report: dict):
	balance = get_stock_balance(ITEM_CODE, WAREHOUSE_NAME)
	if flt(balance) >= SELL_QTY:
		report["steps"].append(f"Stock on hand: {balance}")
		return

	receive = _submit_receive(company)
	report["steps"].append(f"Received stock first: {receive.name} (was {balance}, need {SELL_QTY})")


def _submit_so(company: str, customer: str):
	so = frappe.get_doc(
		{
			"doctype": "Sales Order",
			"customer": customer,
			"company": company,
			"items": [
				{
					"item_code": ITEM_CODE,
					"qty": SO_QTY,
					"rate": RATE,
					"warehouse": WAREHOUSE_NAME,
				}
			],
		}
	)
	so.insert(ignore_permissions=True)
	so.submit()
	return so


def _submit_partial_sell(company: str, sales_order: str):
	txn = frappe.get_doc(
		{
			"doctype": "Stock Transaction",
			"transaction_type": "Sell",
			"company": company,
			"party_name": CUSTOMER_NAME,
			"sales_order": sales_order,
			"default_warehouse": WAREHOUSE_NAME,
			"items": [{"item_code": ITEM_CODE, "qty": SELL_QTY, "rate": RATE}],
		}
	)
	txn.insert(ignore_permissions=True)
	txn.submit()
	return txn


def _verify(sales_order: str, txn, balance_before: float) -> dict:
	so = frappe.get_doc("Sales Order", sales_order)
	so_line = so.items[0]

	stock_entry = _voucher(txn, "Stock Entry")
	sales_invoice = _voucher(txn, "Sales Invoice")
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

	si_gl = 0
	si_total = 0
	si_so_link = None
	if sales_invoice:
		si_gl = frappe.db.count(
			"GL Entry",
			{"voucher_type": "Sales Invoice", "voucher_no": sales_invoice, "is_cancelled": 0},
		)
		si_total = frappe.db.get_value("Sales Invoice", sales_invoice, "grand_total")
		si_so_link = frappe.db.get_value("Sales Invoice", sales_invoice, "sales_order")

	gl_debit_cogs = frappe.db.sql(
		"""
		SELECT SUM(debit) FROM `tabGL Entry`
		WHERE voucher_type = 'Stock Entry' AND voucher_no = %s AND is_cancelled = 0
			AND remarks LIKE %s
		""",
		(stock_entry, f"%{txn.name}%"),
	)[0][0] or 0

	return {
		"so_status_partial": so.status == "Partially Delivered",
		"so_delivered_qty": flt(so_line.delivered_qty) == SELL_QTY,
		"so_remaining_qty": flt(so_line.qty) - flt(so_line.delivered_qty) == SO_QTY - SELL_QTY,
		"txn_linked_to_so": txn.sales_order == sales_order,
		"stock_entry_created": bool(stock_entry),
		"sle_balance_reduced": flt(balance_after) == flt(balance_before) - SELL_QTY,
		"stock_gl_entries": stock_gl >= 2,
		"stock_gl_cogs_amount": flt(gl_debit_cogs) == EXPECTED_SI_AMOUNT,
		"sales_invoice_created": bool(sales_invoice),
		"sales_invoice_linked_to_so": si_so_link == sales_order,
		"sales_invoice_total": flt(si_total) == EXPECTED_SI_AMOUNT,
		"sales_invoice_gl": si_gl >= 2 if sales_invoice else False,
	}


def _print_report(report: dict):
	print("\n" + "=" * 60)
	print("STOCKROOM E2E — STANDARD SELL (SO → SELL)")
	print("=" * 60)
	for step in report.get("steps", []):
		print(f"  ✓ {step}")
	if report.get("sales_order"):
		print(f"\nSales Order: {report['sales_order']}")
	if report.get("transaction"):
		print(f"Stock Transaction: {report['transaction']}")
	print("\nChecks:")
	for check, ok in report.get("checks", {}).items():
		print(f"  {'PASS' if ok else 'FAIL'} — {check}")
	print(f"\nOverall: {'PASS' if report.get('pass') else 'FAIL'}")
	if report.get("error"):
		print(f"Error: {report['error']}")
	print("=" * 60 + "\n")
