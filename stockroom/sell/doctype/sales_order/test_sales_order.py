# Copyright (c) 2026, alool technologies and contributors

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt

from stockroom.sell.doctype.sales_order.sales_order import update_delivered_qty


class TestSalesOrder(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = frappe.db.get_value("Company", {}, "name") or frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": "Test SO Co",
				"abbr": "TSC",
				"default_currency": "USD",
				"country": "United States",
			}
		).insert().name
		if not frappe.db.exists("UOM", "Nos"):
			frappe.get_doc({"doctype": "UOM", "uom_name": "Nos"}).insert()
		if not frappe.db.exists("Item Group", "Products"):
			frappe.get_doc({"doctype": "Item Group", "item_group_name": "Products", "is_group": 0}).insert()

		cls.item = "_Test SO Item"
		if not frappe.db.exists("Item", cls.item):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": cls.item,
					"item_name": "Test SO Item",
					"item_group": "Products",
					"stock_uom": "Nos",
					"is_stock_item": 1,
				}
			).insert()

		cls.customer = "_Test SO Customer"
		if not frappe.db.exists("Customer", cls.customer):
			frappe.get_doc(
				{"doctype": "Customer", "customer_name": cls.customer, "company": cls.company}
			).insert()

	def test_partial_delivery_updates_status(self):
		so = frappe.get_doc(
			{
				"doctype": "Sales Order",
				"customer": self.customer,
				"company": self.company,
				"items": [{"item_code": self.item, "qty": 15, "rate": 10}],
			}
		)
		so.insert()
		so.submit()

		update_delivered_qty(so.name, [{"item_code": self.item, "qty": 5}])
		so.reload()

		self.assertEqual(so.status, "Partially Delivered")
		self.assertEqual(flt(so.items[0].delivered_qty), 5)

		so.cancel()
