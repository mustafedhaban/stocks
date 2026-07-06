frappe.ui.form.on("Purchase Invoice", {
	setup(frm) {
		stockroom.form.setup_company_filters(frm, {
			link_fields: ["supplier"],
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
			],
		});
	},
	refresh(frm) {
		stockroom.form.calc_parent_totals(frm, "items", { total_amount_field: "grand_total" });
		add_record_payment_button(frm);
	},
	company(frm) {
		stockroom.form.on_company_change(frm, ["supplier", "purchase_order"]);
	},
	supplier(frm) {
		if (frm.doc.purchase_order) {
			frm.set_value("purchase_order", "");
		}
	},
});

frappe.ui.form.on("Purchase Invoice Item", {
	qty(frm, cdt, cdn) {
		stockroom.form.update_line_and_totals(frm, cdt, cdn, "items", {
			total_amount_field: "grand_total",
		});
	},
	rate(frm, cdt, cdn) {
		stockroom.form.update_line_and_totals(frm, cdt, cdn, "items", {
			total_amount_field: "grand_total",
		});
	},
	items_remove(frm) {
		stockroom.form.calc_parent_totals(frm, "items", { total_amount_field: "grand_total" });
	},
});

function add_record_payment_button(frm) {
	if (frm.doc.docstatus !== 1) return;
	if (flt(frm.doc.outstanding_amount) <= 0.01) return;
	if (frm.doc.status === "Paid") return;

	frm.add_custom_button(__("Record Payment"), () => {
		stockroom.desk.open_payment_from_invoice(frm, "Pay");
	});
}
