from frappe.model.document import Document
from frappe.utils import flt


class PurchaseOrderItem(Document):
	def validate(self):
		self.amount = flt(self.qty) * flt(self.rate or 0)
