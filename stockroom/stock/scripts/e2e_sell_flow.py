# Copyright (c) 2026, alool technologies and contributors
"""
End-to-end Sell flow test with GL + Sales Invoice verification.

Requires stock on hand — receives first if needed.

Run:
  cd /path/to/demoenv
  bench --site stock execute stockroom.stock.scripts.e2e_sell_flow.run --kwargs "{'cleanup': True}"
"""

from __future__ import annotations

import frappe
from frappe.utils import flt

from stockroom.stock.scripts.e2e_receive_flow import (
	COMPANY_NAME,
	EXPECTED_AMOUNT,
	ITEM_CODE,
	QTY,
	RATE,
	WAREHOUSE_NAME,
	_cleanup as cleanup_e2e,
	_ensure_company,
	_ensure_masters,
	_ensure_posting_profile,
	_ensure_stock_settings,
	_submit_receive,
)
from stockroom.stock.stock_utils import get_stock_balance

CUSTOMER_NAME = "_E2E Retail"


def run(cleanup: bool = False) -> dict:
	frappe.set_user("Administrator")
	if cleanup:
		cleanup_e2e()

	report = {"steps": [], "checks": {}, "pass": False}

	try:
		company = _ensure_company()
		report["steps"].append(f"Company ready: {company}")

		_ensure_posting_profile(company)
		_ensure_stock_settings()
		_ensure_masters(company)
		_ensure_stock_on_hand(company, report)
		balance_before = get_stock_balance(ITEM_CODE, WAREHOUSE_NAME)
		report["balance_before"] = balance_before

		txn = _submit_sell(company)
		report["transaction"] = txn.name
		report["steps"].append(f"Submitted Stock Transaction: {txn.name}")

		report["checks"] = _verify(txn, balance_before)
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
	if flt(balance) >= QTY:
		report["steps"].append(f"Stock on hand: {balance}")
		return

	receive = _submit_receive(company)
	report["steps"].append(f"Received stock first: {receive.name} (was {balance}, need {QTY})")


def _submit_sell(company: str):
	txn = frappe.get_doc(
		{
			"doctype": "Stock Transaction",
			"transaction_type": "Sell",
			"company": company,
			"party_name": CUSTOMER_NAME,
			"default_warehouse": WAREHOUSE_NAME,
			"items": [{"item_code": ITEM_CODE, "qty": QTY, "rate": RATE}],
		}
	)
	txn.insert(ignore_permissions=True)
	txn.submit()
	return txn


def _verify(txn, balance_before: float) -> dict:
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
	if sales_invoice:
		si_gl = frappe.db.count(
			"GL Entry",
			{"voucher_type": "Sales Invoice", "voucher_no": sales_invoice, "is_cancelled": 0},
		)
		si_total = frappe.db.get_value("Sales Invoice", sales_invoice, "grand_total")

	gl_debit_cogs = frappe.db.sql(
		"""
		SELECT SUM(debit) FROM `tabGL Entry`
		WHERE voucher_type = 'Stock Entry' AND voucher_no = %s AND is_cancelled = 0
			AND remarks LIKE %s
		""",
		(stock_entry, f"%{txn.name}%"),
	)[0][0] or 0

	return {
		"stock_entry_created": bool(stock_entry),
		"sle_balance_reduced": flt(balance_after) == flt(balance_before) - QTY,
		"stock_gl_entries": stock_gl >= 2,
		"stock_gl_cogs_amount": flt(gl_debit_cogs) == EXPECTED_AMOUNT,
		"sales_invoice_created": bool(sales_invoice),
		"sales_invoice_total": flt(si_total) == EXPECTED_AMOUNT,
		"sales_invoice_gl": si_gl >= 2 if sales_invoice else False,
		"customer_created": bool(frappe.db.exists("Customer", CUSTOMER_NAME)),
	}


def _voucher(txn, voucher_type: str) -> str | None:
	for row in txn.vouchers:
		if row.voucher_type == voucher_type:
			return row.voucher_no
	return None


def _print_report(report: dict):
	print("\n" + "=" * 60)
	print("STOCKROOM E2E — SELL FLOW")
	print("=" * 60)
	for step in report.get("steps", []):
		print(f"  ✓ {step}")
	if report.get("transaction"):
		print(f"\nTransaction: {report['transaction']}")
	print("\nChecks:")
	for check, ok in report.get("checks", {}).items():
		print(f"  {'PASS' if ok else 'FAIL'} — {check}")
	print(f"\nOverall: {'PASS' if report.get('pass') else 'FAIL'}")
	if report.get("error"):
		print(f"Error: {report['error']}")
	print("=" * 60 + "\n")
