// Stockrooms desk — Browser-inspired task launcher + operations mode
frappe.provide("stockroom.desk");

stockroom.desk.TASK_ROUTES = {
	"Pay Supplier": {
		doctype: "Payment Entry",
		defaults: { payment_type: "Pay", party_type: "Supplier" },
	},
	"Receive Payment": {
		doctype: "Payment Entry",
		defaults: { payment_type: "Receive", party_type: "Customer" },
	},
	"Receive Stock": {
		doctype: "Stock Transaction",
		defaults: { transaction_type: "Receive" },
	},
	Sell: {
		doctype: "Stock Transaction",
		defaults: { transaction_type: "Sell" },
	},
	"Adjust Stock": {
		doctype: "Stock Transaction",
		defaults: { transaction_type: "Adjust" },
	},
	Transfer: {
		doctype: "Stock Transaction",
		defaults: { transaction_type: "Transfer" },
	},
};

stockroom.desk.open_task = function (task, extra_defaults) {
	frappe.route_options = { ...(task.defaults || {}), ...(extra_defaults || {}) };
	frappe.new_doc(task.doctype);
};

stockroom.desk.open_payment_from_invoice = function (frm, payment_type) {
	const is_pay = payment_type === "Pay";
	const outstanding = flt(frm.doc.outstanding_amount);
	if (!outstanding) {
		frappe.msgprint(__("This invoice has no outstanding balance."));
		return;
	}

	stockroom.desk.pending_payment = {
		references: [
			{
				reference_doctype: frm.doctype,
				reference_name: frm.name,
				invoice_total: flt(frm.doc.grand_total),
				outstanding_amount: outstanding,
				allocated_amount: outstanding,
			},
		],
	};

	frappe.route_options = {
		payment_type,
		party_type: is_pay ? "Supplier" : "Customer",
		party: is_pay ? frm.doc.supplier : frm.doc.customer,
		company: frm.doc.company,
		paid_amount: outstanding,
	};
	frappe.new_doc("Payment Entry");
};

stockroom.desk.apply_pending_payment = function (frm) {
	const pending = stockroom.desk.pending_payment;
	if (!pending?.references?.length) return;

	pending.references.forEach((row) => {
		frm.add_child("references", row);
	});
	frm.refresh_field("references");
	let allocated = 0;
	(pending.references || []).forEach((row) => {
		allocated += flt(row.allocated_amount);
	});
	frm.set_value("total_allocated", allocated);
	frm.set_value("difference_amount", flt(frm.doc.paid_amount) - allocated);
	delete stockroom.desk.pending_payment;
};

stockroom.desk.apply_operations_form = function (frm) {
	if (!frappe.boot.stockroom_operations_mode) return;
	if (!frappe.boot.stockroom_ops_doctypes?.includes(frm.doctype)) return;

	frm.page.wrapper.addClass("stockroom-ops-form-page");
	document.body.classList.add("stockroom-ops-active");

	const hide = ["naming_series", "amended_from"];
	hide.forEach((field) => {
		if (frm.fields_dict[field]) {
			frm.set_df_property(field, "hidden", 1);
		}
	});
};

stockroom.desk.setup_task_shortcuts = function () {
	document.addEventListener(
		"click",
		(e) => {
			const widget = e.target.closest(".shortcut-widget-box");
			if (!widget) return;

			const label = widget.getAttribute("aria-label");
			const task = stockroom.desk.TASK_ROUTES[label];
			if (!task) return;

			e.preventDefault();
			e.stopImmediatePropagation();
			stockroom.desk.open_task(task);
		},
		true
	);
};

$(document).on("form-refresh", (e, frm) => {
	stockroom.desk.apply_operations_form(frm);
});

frappe.ready(() => {
	stockroom.desk.setup_task_shortcuts();
	if (frappe.boot.stockroom_operations_mode) {
		document.body.classList.add("stockroom-ops-mode");
	}
});
