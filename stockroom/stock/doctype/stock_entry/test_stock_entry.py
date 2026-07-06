# Copyright (c) 2026, alool technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase


class TestStockEntry(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = frappe.db.get_value("Company", {}, "name")
		if not cls.company:
			cls.company = frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": "Test Stock Co",
					"abbr": "TSC",
					"default_currency": "USD",
					"country": "United States",
				}
			).insert().name

		if not frappe.db.exists("UOM", "Nos"):
			frappe.get_doc({"doctype": "UOM", "uom_name": "Nos"}).insert()

		if not frappe.db.exists("Item Group", "Products"):
			frappe.get_doc({"doctype": "Item Group", "item_group_name": "Products", "is_group": 0}).insert()

	def test_material_receipt_updates_balance(self):
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "_Test Stock Item",
				"item_name": "Test Stock Item",
				"item_group": "Products",
				"stock_uom": "Nos",
				"is_stock_item": 1,
			}
		).insert()

		warehouse = frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": "_Test Main WH",
				"company": self.company,
			}
		).insert()

		se = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Receipt",
				"company": self.company,
				"items": [
					{
						"item_code": item.name,
						"qty": 10,
						"t_warehouse": warehouse.name,
					}
				],
			}
		)
		se.insert()
		se.submit()

		balance = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": item.name, "warehouse": warehouse.name, "is_cancelled": 0},
			"qty_after_transaction",
		)
		self.assertEqual(balance, 10)

		se.cancel()
		cancelled = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": item.name, "warehouse": warehouse.name},
			"is_cancelled",
		)
		self.assertEqual(cancelled, 1)
