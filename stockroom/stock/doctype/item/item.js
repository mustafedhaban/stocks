frappe.ui.form.on("Item", {
	refresh(frm) {
		toggle_stock_uom(frm);
	},
	is_stock_item(frm) {
		toggle_stock_uom(frm);
	},
});

function toggle_stock_uom(frm) {
	const is_stock = frm.doc.is_stock_item;
	frm.toggle_reqd("stock_uom", is_stock);
	frm.toggle_display("stock_uom", is_stock);
}
