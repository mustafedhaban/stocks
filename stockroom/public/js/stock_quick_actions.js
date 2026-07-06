// Quick action shortcuts — preset transaction_type on new Stock Transaction
frappe.provide("stockroom.stock");

const QUICK_ACTIONS = {
	Receive: "Receive Stock",
	Sell: "Sell",
	Adjust: "Adjust Stock",
	Transfer: "Transfer",
};

Object.entries(QUICK_ACTIONS).forEach(([type, label]) => {
	frappe.ui.keys.add_shortcut({
		shortcut: "",
		action: () => {
			frappe.new_doc("Stock Transaction", { transaction_type: type });
		},
		description: label,
		page: "Stock",
	});
});
