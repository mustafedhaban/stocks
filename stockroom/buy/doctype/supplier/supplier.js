frappe.ui.form.on("Supplier", {
	setup(frm) {
		frm.set_query("company", () => ({ filters: { disabled: 0 } }));
	},
});
