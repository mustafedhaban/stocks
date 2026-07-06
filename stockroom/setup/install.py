# Copyright (c) 2026, alool technologies and contributors

import frappe

ROLES = ("Stock User", "Stock Manager", "Buy User", "Sell User", "Accounts User")


def after_install():
	for role in ROLES:
		if frappe.db.exists("Role", role):
			continue
		frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)
	frappe.db.commit()
