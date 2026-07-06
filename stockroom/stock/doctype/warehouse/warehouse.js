frappe.ui.form.on("Warehouse", {
	setup(frm) {
		frm.set_query("parent_warehouse", () => ({
			filters: {
				company: frm.doc.company,
				is_group: 1,
				disabled: 0,
				name: ["!=", frm.doc.name],
			},
		}));
		frm.set_query("company", () => ({ filters: { disabled: 0 } }));
	},
	refresh(frm) {
		toggle_parent_warehouse(frm);
	},
	is_group(frm) {
		if (frm.doc.is_group) {
			frm.set_value("parent_warehouse", "");
		}
		toggle_parent_warehouse(frm);
	},
	company(frm) {
		frm.set_value("parent_warehouse", "");
	},
});

function toggle_parent_warehouse(frm) {
	const show_parent = !frm.doc.is_group;
	frm.toggle_display("parent_warehouse", show_parent);
	frm.toggle_reqd("parent_warehouse", false);
}
