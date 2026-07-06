frappe.ui.form.on("Stock Settings", {
	setup(frm) {
		frm.set_query("default_receiving_warehouse", () => ({
			filters: { disabled: 0, is_group: 0 },
		}));
		frm.set_query("default_shipping_warehouse", () => ({
			filters: { disabled: 0, is_group: 0 },
		}));
	},
	refresh(frm) {
		toggle_billing_section(frm);
	},
	default_workflow_mode(frm) {
		toggle_billing_section(frm);
	},
});

function toggle_billing_section(frm) {
	const quick = frm.doc.default_workflow_mode === "Quick";
	frm.toggle_display("billing_section", quick);
	frm.toggle_display("auto_create_purchase_invoice", quick);
	frm.toggle_display("auto_create_sales_invoice", quick);
	frm.toggle_display("auto_submit_invoices", quick);
	frm.toggle_display("column_break_billing", quick);
}
