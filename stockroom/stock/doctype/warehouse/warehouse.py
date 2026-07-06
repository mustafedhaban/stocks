# Copyright (c) 2026, alool technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Warehouse(Document):
	def validate(self):
		if self.is_group:
			if self.parent_warehouse:
				frappe.throw(_("Group warehouses cannot have a parent warehouse"))
		elif self.parent_warehouse:
			if not frappe.db.get_value("Warehouse", self.parent_warehouse, "is_group"):
				frappe.throw(_("Parent Warehouse must be a group warehouse"))
			if frappe.db.get_value("Warehouse", self.parent_warehouse, "company") != self.company:
				frappe.throw(_("Parent Warehouse must belong to the same company"))
