# Copyright (c) 2026, alool technologies and contributors
"""
End-to-end payment flow: pay supplier (Purchase Invoice) and receive from customer (Sales Invoice).

Run:
  cd /path/to/demoenv
  bench --site stock execute stockroom.stock.scripts.e2e_payment_flow.run --kwargs "{'cleanup': True}"
"""

from __future__ import annotations

import frappe
from frappe.utils import flt

from stockroom.stock.scripts.e2e_receive_flow import (
	COMPANY_NAME,
	EXPECTED_AMOUNT,
	SUPPLIER_NAME,
	_cleanup as cleanup_e2e,
	_ensure_company,
	_ensure_masters,
	_ensure_posting_profile,
	_ensure_stock_settings,
	_submit_receive,
	_voucher,
)
from stockroom.stock.scripts.e2e_sell_flow import CUSTOMER_NAME, _submit_sell


def run(cleanup: bool = False) -> dict:
	frappe.set_user("Administrator")
	if cleanup:
		cleanup_e2e()

	report = {"steps": [], "checks": {}, "pass": False}

	try:
		company = _ensure_company()
		_ensure_posting_profile(company)
		_ensure_stock_settings()
		_ensure_masters(company)
		bank = _ensure_bank_account(company)

		receive_txn = _submit_receive(company)
		pi_name = _voucher(receive_txn, "Purchase Invoice")
		report["steps"].append(f"Purchase Invoice: {pi_name}")

		sell_txn = _submit_sell(company)
		si_name = _voucher(sell_txn, "Sales Invoice")
		report["steps"].append(f"Sales Invoice: {si_name}")

		pay = _submit_pay_supplier(company, bank, pi_name)
		report["pay_entry"] = pay.name
		report["steps"].append(f"Payment Entry (Pay): {pay.name}")

		receive = _submit_receive_from_customer(company, bank, si_name)
		report["receive_entry"] = receive.name
		report["steps"].append(f"Payment Entry (Receive): {receive.name}")

		report["checks"] = _verify(pi_name, si_name, pay.name, receive.name)
		report["pass"] = all(report["checks"].values())
		frappe.db.commit()
	except Exception as e:
		frappe.db.rollback()
		report["error"] = str(e)
		raise
	finally:
		_print_report(report)

	return report


def _ensure_bank_account(company: str) -> str:
	company_doc = frappe.get_doc("Company", company)
	bank = company_doc.default_bank_account or company_doc.default_cash_account
	if not bank:
		bank = frappe.db.get_value(
			"Account",
			{"company": company, "account_type": "Bank", "is_group": 0},
			"name",
		)
	if not bank:
		frappe.throw(f"No bank/cash account found for {company}")
	return bank


def _submit_pay_supplier(company: str, bank: str, pi_name: str):
	outstanding = flt(frappe.db.get_value("Purchase Invoice", pi_name, "outstanding_amount"))
	amount = outstanding or EXPECTED_AMOUNT
	payment = frappe.get_doc(
		{
			"doctype": "Payment Entry",
			"payment_type": "Pay",
			"company": company,
			"party_type": "Supplier",
			"party": SUPPLIER_NAME,
			"paid_from": bank,
			"paid_amount": amount,
			"references": [
				{
					"reference_doctype": "Purchase Invoice",
					"reference_name": pi_name,
					"allocated_amount": amount,
				}
			],
		}
	)
	payment.insert(ignore_permissions=True)
	payment.submit()
	return payment


def _submit_receive_from_customer(company: str, bank: str, si_name: str):
	outstanding = flt(frappe.db.get_value("Sales Invoice", si_name, "outstanding_amount"))
	amount = outstanding or EXPECTED_AMOUNT
	payment = frappe.get_doc(
		{
			"doctype": "Payment Entry",
			"payment_type": "Receive",
			"company": company,
			"party_type": "Customer",
			"party": CUSTOMER_NAME,
			"paid_to": bank,
			"paid_amount": amount,
			"references": [
				{
					"reference_doctype": "Sales Invoice",
					"reference_name": si_name,
					"allocated_amount": amount,
				}
			],
		}
	)
	payment.insert(ignore_permissions=True)
	payment.submit()
	return payment


def _verify(pi_name: str, si_name: str, pay_name: str, receive_name: str) -> dict:
	pi = frappe.db.get_value(
		"Purchase Invoice",
		pi_name,
		["status", "paid_amount", "outstanding_amount", "grand_total"],
		as_dict=True,
	)
	si = frappe.db.get_value(
		"Sales Invoice",
		si_name,
		["status", "paid_amount", "outstanding_amount", "grand_total"],
		as_dict=True,
	)

	pay_gl = frappe.db.count(
		"GL Entry",
		{"voucher_type": "Payment Entry", "voucher_no": pay_name, "is_cancelled": 0},
	)
	receive_gl = frappe.db.count(
		"GL Entry",
		{"voucher_type": "Payment Entry", "voucher_no": receive_name, "is_cancelled": 0},
	)

	return {
		"pi_paid": pi.status == "Paid" and flt(pi.outstanding_amount) <= 0.01,
		"pi_amount": flt(pi.paid_amount) == flt(pi.grand_total),
		"si_paid": si.status == "Paid" and flt(si.outstanding_amount) <= 0.01,
		"si_amount": flt(si.paid_amount) == flt(si.grand_total),
		"pay_gl_entries": pay_gl >= 2,
		"receive_gl_entries": receive_gl >= 2,
	}


def _print_report(report: dict):
	print("\n" + "=" * 60)
	print("STOCKROOM E2E — PAYMENT FLOW")
	print("=" * 60)
	for step in report.get("steps", []):
		print(f"  • {step}")
	if report.get("checks"):
		print("\nChecks:")
		for key, ok in report["checks"].items():
			print(f"  {'PASS' if ok else 'FAIL'} — {key}")
	print(f"\nResult: {'PASS' if report.get('pass') else 'FAIL'}")
	if report.get("error"):
		print(f"Error: {report['error']}")
	print("=" * 60 + "\n")
