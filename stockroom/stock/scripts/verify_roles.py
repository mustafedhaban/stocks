# Copyright (c) 2026, alool technologies and contributors
"""Verify operational roles and DocType permissions exist."""

from __future__ import annotations

import frappe

ROLES = ("Stock User", "Stock Manager", "Buy User", "Sell User")

EXPECTED = {
	"Item": ROLES,
	"Stock Transaction": ROLES,
	"Purchase Order": ("Buy User", "Stock Manager"),
	"Sales Order": ("Sell User", "Stock Manager"),
}


def run() -> dict:
	from stockroom.setup.install import after_install

	after_install()

	report = {"roles": {}, "permissions": {}, "pass": True}

	for role in ROLES:
		ok = bool(frappe.db.exists("Role", role))
		report["roles"][role] = ok
		if not ok:
			report["pass"] = False

	for doctype, roles in EXPECTED.items():
		for role in roles:
			ok = bool(frappe.db.exists("DocPerm", {"parent": doctype, "role": role, "permlevel": 0}))
			key = f"{doctype}:{role}"
			report["permissions"][key] = ok
			if not ok:
				report["pass"] = False

	print("\n" + "=" * 60)
	print("STOCKROOM — ROLE / PERMISSION CHECK")
	print("=" * 60)
	for role, ok in report["roles"].items():
		print(f"  {'PASS' if ok else 'FAIL'} — role {role}")
	for key, ok in report["permissions"].items():
		print(f"  {'PASS' if ok else 'FAIL'} — DocPerm {key}")
	print(f"\nOverall: {'PASS' if report['pass'] else 'FAIL'}")
	print("=" * 60 + "\n")
	return report
