frappe.ui.form.on("Sales Order", {
	setup(frm) {
		stockroom.form.setup_company_filters(frm, {
			link_fields: ["customer"],
			child_tables: [{ table: "items", warehouse_field: "warehouse" }],
		});
	},
	refresh(frm) {
		stockroom.form.calc_parent_totals(frm, "items", {
			total_qty_field: "total_qty",
			total_amount_field: "grand_total",
		});
	},
	company(frm) {
		stockroom.form.on_company_change(frm, ["customer"]);
	},
});

frappe.ui.form.on("Sales Order Item", {
	qty(frm, cdt, cdn) {
		stockroom.form.update_line_and_totals(frm, cdt, cdn, "items", {
			total_qty_field: "total_qty",
			total_amount_field: "grand_total",
		});
	},
	rate(frm, cdt, cdn) {
		stockroom.form.update_line_and_totals(frm, cdt, cdn, "items", {
			total_qty_field: "total_qty",
			total_amount_field: "grand_total",
		});
	},
	items_remove(frm) {
		stockroom.form.calc_parent_totals(frm, "items", {
			total_qty_field: "total_qty",
			total_amount_field: "grand_total",
		});
	},
});
