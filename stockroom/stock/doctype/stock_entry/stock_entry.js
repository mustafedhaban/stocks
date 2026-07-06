frappe.ui.form.on("Stock Entry", {
	setup(frm) {
		setup_link_filters(frm);
	},
	refresh(frm) {
		set_warehouse_visibility(frm);
	},
	stock_entry_type(frm) {
		set_warehouse_visibility(frm);
	},
	company(frm) {
		setup_link_filters(frm);
	},
});

frappe.ui.form.on("Stock Entry Detail", {
	items_add(frm) {
		set_warehouse_visibility(frm);
	},
});

function setup_link_filters(frm) {
	const leaf_wh = () => ({
		filters: stockroom.form.company_filters(frm.doc.company, { is_group: 0 }),
	});
	frm.set_query("company", () => ({ filters: { disabled: 0 } }));
	frm.set_query("s_warehouse", "items", leaf_wh);
	frm.set_query("t_warehouse", "items", leaf_wh);
}

function set_warehouse_visibility(frm) {
	const type = frm.doc.stock_entry_type;
	const grid = frm.fields_dict.items?.grid;
	if (!grid) return;

	const show_source = ["Material Issue", "Material Transfer"].includes(type);
	const show_target = ["Material Receipt", "Material Transfer", "Stock Reconciliation"].includes(type);

	grid.update_docfield_property("s_warehouse", "hidden", !show_source);
	grid.update_docfield_property("t_warehouse", "hidden", !show_target);
}
