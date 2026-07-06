frappe.ui.form.on("Stock Transaction", {
	setup(frm) {
		apply_route_defaults(frm);
		setup_link_filters(frm);
	},
	onload(frm) {
		set_field_visibility(frm);
	},
	refresh(frm) {
		set_field_visibility(frm);
		recalculate_totals(frm);
	},
	transaction_type(frm) {
		set_field_visibility(frm);
		recalculate_totals(frm);
	},
	company(frm) {
		stockroom.form.on_company_change(frm, [
			"supplier",
			"customer",
			"purchase_order",
			"sales_order",
			"default_warehouse",
			"source_warehouse",
			"target_warehouse",
		]);
	},
	recalculate(frm) {
		recalculate_totals(frm);
	},
});

frappe.ui.form.on("Stock Transaction Item", {
	qty(frm, cdt, cdn) {
		stockroom.form.update_line_and_totals(frm, cdt, cdn, "items", {
			total_qty_field: "total_qty",
			total_amount_field: "total_amount",
		});
	},
	rate(frm, cdt, cdn) {
		stockroom.form.update_line_and_totals(frm, cdt, cdn, "items", {
			total_qty_field: "total_qty",
			total_amount_field: "total_amount",
		});
	},
	items_remove(frm) {
		recalculate_totals(frm);
	},
});

function apply_route_defaults(frm) {
	if (frm.is_new() && frappe.route_options?.transaction_type) {
		frm.set_value("transaction_type", frappe.route_options.transaction_type);
		frappe.route_options = {};
	}
}

function setup_link_filters(frm) {
	stockroom.form.setup_company_filters(frm, {
		link_fields: ["supplier", "customer"],
		warehouse_fields: ["default_warehouse", "source_warehouse", "target_warehouse"],
		child_tables: [{ table: "items", warehouse_field: "warehouse" }],
		custom: [
			{
				field: "purchase_order",
				filters_fn: () => ({
					filters: {
						company: frm.doc.company,
						docstatus: 1,
						supplier: frm.doc.supplier || "",
					},
				}),
			},
			{
				field: "sales_order",
				filters_fn: () => ({
					filters: {
						company: frm.doc.company,
						docstatus: 1,
						customer: frm.doc.customer || "",
					},
				}),
			},
		],
	});
}

function set_field_visibility(frm) {
	const type = frm.doc.transaction_type;
	const grid = frm.fields_dict.items?.grid;
	if (!grid) return;

	const show_party = ["Receive", "Sell"].includes(type);
	const show_default_wh = ["Receive", "Sell", "Adjust"].includes(type);
	const show_transfer_wh = type === "Transfer";
	const show_rate = ["Receive", "Sell"].includes(type);

	frm.toggle_display("party_section", show_party);
	frm.toggle_display("party_name", show_party);
	frm.toggle_display("default_warehouse", show_default_wh);
	frm.toggle_display("source_warehouse", show_transfer_wh);
	frm.toggle_display("target_warehouse", show_transfer_wh);

	const show_line_wh = show_default_wh;
	const show_s = type === "Transfer";
	const show_t = type === "Transfer";

	grid.update_docfield_property("warehouse", "hidden", !show_line_wh);
	grid.update_docfield_property("s_warehouse", "hidden", !show_s);
	grid.update_docfield_property("t_warehouse", "hidden", !show_t);
	grid.update_docfield_property("rate", "hidden", !show_rate);
	grid.update_docfield_property("amount", "hidden", !show_rate);

	if (type === "Adjust") {
		grid.update_docfield_property("qty", "label", __("Counted Qty"));
	} else {
		grid.update_docfield_property("qty", "label", __("Qty"));
	}
}

function recalculate_totals(frm) {
	stockroom.form.calc_parent_totals(frm, "items", {
		total_qty_field: "total_qty",
		total_amount_field: "total_amount",
	});
}
