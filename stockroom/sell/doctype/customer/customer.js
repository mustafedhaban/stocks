frappe.ui.form.on("Customer", {
	setup(frm) {
		frm.set_query("company", () => ({ filters: { disabled: 0 } }));
	},
});
