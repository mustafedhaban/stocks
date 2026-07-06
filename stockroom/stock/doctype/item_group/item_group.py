# Copyright (c) 2026, alool technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.nestedset import NestedSet


class ItemGroup(NestedSet):
	nsm_parent_field = "parent_item_group"
