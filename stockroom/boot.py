# Copyright (c) 2026, alool technologies and contributors

import frappe

OPS_ROLES = frozenset({"Stock User", "Buy User", "Sell User", "Accounts User", "Stock Manager"})

OPS_DOCTYPES = frozenset(
	{
		"Stock Transaction",
		"Payment Entry",
		"Purchase Invoice",
		"Sales Invoice",
		"Purchase Order",
		"Sales Order",
	}
)


def boot_session(bootinfo):
	roles = set(frappe.get_roles())
	bootinfo.stockroom_operations_mode = bool(roles & OPS_ROLES) and "System Manager" not in roles
	bootinfo.stockroom_ops_doctypes = list(OPS_DOCTYPES)
