# Copyright (c) 2026, alool technologies and contributors

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt

from stockroom.buy.doctype.purchase_order.purchase_order import PurchaseOrder, update_received_qty


class TestPurchaseOrder(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = cls._ensure_company()
		cls._ensure_uom()
		cls._ensure_item_group()
		cls.item = cls._ensure_item()
		cls.supplier = cls._ensure_supplier()

	@classmethod
	def _ensure_company(cls):
		name = frappe.db.get_value("Company", {}, "name")
		if name:
			return name
		return frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": "Test PO Co",
				"abbr": "TPC",
				"default_currency": "USD",
				"country": "United States",
			}
		).insert().name

	@classmethod
	def _ensure_uom(cls):
		if not frappe.db.exists("UOM", "Nos"):
			frappe.get_doc({"doctype": "UOM", "uom_name": "Nos"}).insert()

	@classmethod
	def _ensure_item_group(cls):
		if not frappe.db.exists("Item Group", "Products"):
			frappe.get_doc({"doctype": "Item Group", "item_group_name": "Products", "is_group": 0}).insert()

	@classmethod
	def _ensure_item(cls):
		code = "_Test PO Item"
		if frappe.db.exists("Item", code):
			return code
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": code,
				"item_name": "Test PO Item",
				"item_group": "Products",
				"stock_uom": "Nos",
				"is_stock_item": 1,
			}
		).insert()
		return code

	@classmethod
	def _ensure_supplier(cls):
		name = "_Test PO Supplier"
		if frappe.db.exists("Supplier", name):
			return name
		frappe.get_doc(
			{"doctype": "Supplier", "supplier_name": name, "company": cls.company}
		).insert()
		return name

	def test_validate_computes_totals(self):
		po = PurchaseOrder(
			{
				"doctype": "Purchase Order",
				"supplier": self.supplier,
				"company": self.company,
				"items": [{"item_code": self.item, "qty": 4, "rate": 2.5}],
			}
		)
		po.run_method("validate")
		self.assertEqual(flt(po.grand_total), 10)
		self.assertEqual(flt(po.total_qty), 4)

	def test_partial_receive_updates_status(self):
		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": self.supplier,
				"company": self.company,
				"items": [{"item_code": self.item, "qty": 20, "rate": 5}],
			}
		)
		po.insert()
		po.submit()

		update_received_qty(po.name, [{"item_code": self.item, "qty": 8}])
		po.reload()
		self.assertEqual(po.status, "Partially Received")
		self.assertEqual(flt(po.items[0].received_qty), 8)

		update_received_qty(po.name, [{"item_code": self.item, "qty": 12}])
		po.reload()
		self.assertEqual(po.status, "Completed")

		po.cancel()
