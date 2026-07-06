# Copyright (c) 2026, alool technologies and contributors

import frappe
from frappe import _


def get_or_create_supplier(name: str, company: str) -> str:
	name = (name or "").strip()
	if not name:
		frappe.throw(_("Supplier name is required"))
	if frappe.db.exists("Supplier", name):
		return name
	doc = frappe.get_doc({"doctype": "Supplier", "supplier_name": name, "company": company})
	doc.insert(ignore_permissions=True)
	return doc.name


def get_or_create_customer(name: str, company: str) -> str:
	name = (name or "").strip()
	if not name:
		frappe.throw(_("Customer name is required"))
	if frappe.db.exists("Customer", name):
		return name
	doc = frappe.get_doc({"doctype": "Customer", "customer_name": name, "company": company})
	doc.insert(ignore_permissions=True)
	return doc.name
