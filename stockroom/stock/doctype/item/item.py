# Copyright (c) 2026, alool technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Item(Document):
	def validate(self):
		if self.is_stock_item and not self.stock_uom:
			frappe.throw(_("Default Unit of Measure is required for stock items"))
