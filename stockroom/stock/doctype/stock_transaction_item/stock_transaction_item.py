# Copyright (c) 2026, alool technologies and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.utils import flt


class StockTransactionItem(Document):
	def validate(self):
		self.amount = flt(self.qty) * flt(self.rate or 0)
