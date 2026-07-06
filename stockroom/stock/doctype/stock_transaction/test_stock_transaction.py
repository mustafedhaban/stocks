# Copyright (c) 2026, alool technologies and contributors

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt


class TestStockTransaction(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = frappe.db.get_value("Company", {}, "name")
		if not cls.company:
			cls.company = frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": "Test STX Co",
					"abbr": "TST",
					"default_currency": "USD",
					"country": "United States",
				}
			).insert().name
		if not frappe.db.exists("UOM", "Nos"):
			frappe.get_doc({"doctype": "UOM", "uom_name": "Nos"}).insert()
		if not frappe.db.exists("Item Group", "Products"):
			frappe.get_doc({"doctype": "Item Group", "item_group_name": "Products", "is_group": 0}).insert()

		cls.item = "_Test STX Item"
		if not frappe.db.exists("Item", cls.item):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": cls.item,
					"item_name": "Test STX Item",
					"item_group": "Products",
					"stock_uom": "Nos",
					"is_stock_item": 1,
				}
			).insert()

		cls.warehouse = "_Test STX WH"
		if not frappe.db.exists("Warehouse", cls.warehouse):
			frappe.get_doc(
				{"doctype": "Warehouse", "warehouse_name": cls.warehouse, "company": cls.company}
			).insert()

	def test_receive_creates_stock_entry(self):
		txn = frappe.get_doc(
			{
				"doctype": "Stock Transaction",
				"transaction_type": "Receive",
				"company": self.company,
				"party_name": "Test Supplier",
				"default_warehouse": self.warehouse,
				"items": [{"item_code": self.item, "qty": 3, "rate": 2}],
			}
		)
		txn.insert()
		txn.submit()

		self.assertTrue(any(v.voucher_type == "Stock Entry" for v in txn.vouchers))
		self.assertEqual(flt(txn.total_amount), 6)

		txn.cancel()

	def test_validate_rejects_group_warehouse(self):
		group_wh = "_Test Group WH"
		if not frappe.db.exists("Warehouse", group_wh):
			frappe.get_doc(
				{
					"doctype": "Warehouse",
					"warehouse_name": group_wh,
					"company": self.company,
					"is_group": 1,
				}
			).insert()

		txn = frappe.get_doc(
			{
				"doctype": "Stock Transaction",
				"transaction_type": "Receive",
				"company": self.company,
				"default_warehouse": group_wh,
				"items": [{"item_code": self.item, "qty": 1}],
			}
		)
		with self.assertRaises(frappe.ValidationError):
			txn.insert()
