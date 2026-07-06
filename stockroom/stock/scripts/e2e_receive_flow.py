# Copyright (c) 2026, alool technologies and contributors
"""
End-to-end Receive flow test with GL + Purchase Invoice verification.

Run:
  cd /path/to/demoenv
  bench --site stock execute stockroom.stock.scripts.e2e_receive_flow.run --kwargs "{'cleanup': True}"
"""

from __future__ import annotations

import frappe
from frappe.utils import cint, flt

from stockroom.stock.stock_utils import get_stock_balance

PREFIX = "_E2E"
COMPANY_NAME = f"{PREFIX} Test Co"
ITEM_CODE = f"{PREFIX}-WIDGET"
SUPPLIER_NAME = f"{PREFIX} Supplies"
WAREHOUSE_NAME = f"{PREFIX} Main WH"
QTY = 10
RATE = 5.0
EXPECTED_AMOUNT = QTY * RATE


def run(cleanup: bool = False) -> dict:
	"""Bootstrap masters, submit a Receive transaction, verify ledgers."""
	frappe.set_user("Administrator")
	if cleanup:
		_cleanup()

	report = {"steps": [], "checks": {}, "pass": False}

	try:
		company = _ensure_company()
		report["steps"].append(f"Company ready: {company}")

		_ensure_posting_profile(company)
		_ensure_stock_settings()
		_ensure_masters(company)

		balance_before = get_stock_balance(ITEM_CODE, WAREHOUSE_NAME)
		report["balance_before"] = balance_before

		txn = _submit_receive(company)
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


def _ensure_company() -> str:
	if frappe.db.exists("Company", COMPANY_NAME):
		company = frappe.get_doc("Company", COMPANY_NAME)
		if cint(company.enable_perpetual_inventory) and company.default_inventory_account:
			return company.name
	else:
		if not frappe.db.exists("Currency", "USD"):
			frappe.get_doc({"doctype": "Currency", "currency_name": "USD", "enabled": 1}).insert(
				ignore_permissions=True
			)
		company = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": COMPANY_NAME,
				"abbr": "E2E",
				"default_currency": "USD",
				"country": "United States",
				"create_chart_of_accounts_based_on": "Standard Template",
				"chart_of_accounts": "Standard",
				"enable_perpetual_inventory": 1,
			}
		)
		company.insert(ignore_permissions=True)

	if not frappe.db.exists("Account", {"company": company.name, "is_group": 0}):
		frappe.throw(f"Chart of accounts not created for {company.name}")

	company.enable_perpetual_inventory = 1
	company.update_default_account = True
	if hasattr(company, "set_default_accounts"):
		company.set_default_accounts()
	company.save(ignore_permissions=True)

	if not company.default_inventory_account:
		stock_acct = frappe.db.get_value(
			"Account",
			{"company": company.name, "account_type": "Stock", "is_group": 0},
			"name",
		)
		if stock_acct:
			company.db_set("default_inventory_account", stock_acct)

	return company.name


def _ensure_posting_profile(company: str):
	if frappe.db.exists("Posting Profile", company):
		return
	profile = frappe.get_doc({"doctype": "Posting Profile", "company": company})
	profile.insert(ignore_permissions=True)


def _ensure_stock_settings():
	settings = frappe.get_single("Stock Settings")
	settings.auto_create_purchase_invoice = 1
	settings.auto_create_sales_invoice = 1
	settings.auto_submit_invoices = 1
	settings.default_workflow_mode = "Quick"
	if frappe.db.exists("Warehouse", WAREHOUSE_NAME):
		settings.default_receiving_warehouse = WAREHOUSE_NAME
		settings.default_shipping_warehouse = WAREHOUSE_NAME
	else:
		settings.default_receiving_warehouse = None
		settings.default_shipping_warehouse = None
	settings.save(ignore_permissions=True)


def _ensure_masters(company: str):
	if not frappe.db.exists("UOM", "Nos"):
		frappe.get_doc({"doctype": "UOM", "uom_name": "Nos"}).insert(ignore_permissions=True)

	if not frappe.db.exists("Item Group", f"{PREFIX} Products"):
		frappe.get_doc(
			{"doctype": "Item Group", "item_group_name": f"{PREFIX} Products", "is_group": 0}
		).insert(ignore_permissions=True)

	if not frappe.db.exists("Item", ITEM_CODE):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": ITEM_CODE,
				"item_name": "E2E Widget",
				"item_group": f"{PREFIX} Products",
				"stock_uom": "Nos",
				"is_stock_item": 1,
				"company": company,
			}
		).insert(ignore_permissions=True)

	if not frappe.db.exists("Warehouse", WAREHOUSE_NAME):
		frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": WAREHOUSE_NAME,
				"company": company,
			}
		).insert(ignore_permissions=True)


def _submit_receive(company: str):
	txn = frappe.get_doc(
		{
			"doctype": "Stock Transaction",
			"transaction_type": "Receive",
			"company": company,
			"party_name": SUPPLIER_NAME,
			"default_warehouse": WAREHOUSE_NAME,
			"items": [{"item_code": ITEM_CODE, "qty": QTY, "rate": RATE}],
		}
	)
	txn.insert(ignore_permissions=True)
	txn.submit()
	return txn


def _verify(txn, balance_before: float) -> dict:
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
	if purchase_invoice:
		pi_gl = frappe.db.count(
			"GL Entry",
			{"voucher_type": "Purchase Invoice", "voucher_no": purchase_invoice, "is_cancelled": 0},
		)
		pi_total = frappe.db.get_value("Purchase Invoice", purchase_invoice, "grand_total")

	gl_debit_stock = frappe.db.sql(
		"""
		SELECT SUM(debit) FROM `tabGL Entry`
		WHERE voucher_type = 'Stock Entry' AND voucher_no = %s AND is_cancelled = 0
			AND remarks LIKE %s
		""",
		(stock_entry, f"%{txn.name}%"),
	)[0][0] or 0

	return {
		"stock_entry_created": bool(stock_entry),
		"sle_balance_increased": flt(balance_after) == flt(balance_before) + QTY,
		"stock_gl_entries": stock_gl >= 2,
		"stock_gl_amount": flt(gl_debit_stock) == EXPECTED_AMOUNT,
		"purchase_invoice_created": bool(purchase_invoice),
		"purchase_invoice_total": flt(pi_total) == EXPECTED_AMOUNT,
		"purchase_invoice_gl": pi_gl >= 2 if purchase_invoice else False,
		"supplier_created": bool(frappe.db.exists("Supplier", SUPPLIER_NAME)),
	}


def _voucher(txn, voucher_type: str) -> str | None:
	for row in txn.vouchers:
		if row.voucher_type == voucher_type:
			return row.voucher_no
	return None


def _cleanup():
	"""Remove prior E2E documents for the test company (best-effort)."""
	if not frappe.db.exists("Company", COMPANY_NAME):
		return

	for dt in (
		"Payment Entry",
		"Sales Invoice",
		"Purchase Invoice",
		"Stock Transaction",
		"Sales Order",
		"Purchase Order",
	):
		for name in frappe.get_all(dt, filters={"company": COMPANY_NAME}, pluck="name", order_by="creation desc"):
			_try_delete(dt, name)

	for name in frappe.get_all("Stock Entry", filters={"company": COMPANY_NAME}, pluck="name", order_by="creation desc"):
		_try_delete("Stock Entry", name)

	# Second pass — catch any submitted vouchers missed on first pass
	for dt in ("Payment Entry", "Sales Invoice", "Purchase Invoice", "Stock Transaction", "Stock Entry"):
		for name in frappe.get_all(
			dt,
			filters={"company": COMPANY_NAME, "docstatus": 1} if dt != "Stock Entry" else {"company": COMPANY_NAME, "docstatus": 1},
			pluck="name",
			order_by="creation desc",
		):
			_try_delete(dt, name)

	for dt in ("Item", "Warehouse", "Supplier", "Customer"):
		for name in frappe.get_all(dt, filters={"name": ("like", f"{PREFIX}%")}, pluck="name"):
			_try_delete(dt, name, force=True)


def _try_delete(doctype: str, name: str, force: bool = False):
	try:
		doc = frappe.get_doc(doctype, name)
		if doc.docstatus == 1:
			doc.cancel()
			frappe.db.commit()
		if force:
			frappe.delete_doc(doctype, name, force=1)
		else:
			frappe.delete_doc(doctype, name)
		frappe.db.commit()
	except Exception:
		frappe.db.rollback()


def _print_report(report: dict):
	print("\n" + "=" * 60)
	print("STOCKROOM E2E — RECEIVE FLOW")
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
