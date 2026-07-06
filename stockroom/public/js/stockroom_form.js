frappe.provide("stockroom.form");

stockroom.form.calc_row_amount = function (cdt, cdn) {
	const row = frappe.get_doc(cdt, cdn);
	const amount = flt(row.qty) * flt(row.rate || 0);
	frappe.model.set_value(cdt, cdn, "amount", amount);
};

stockroom.form.calc_parent_totals = function (frm, table_field, options = {}) {
	const { total_qty_field = null, total_amount_field = "grand_total" } = options;
	let qty = 0;
	let amount = 0;

	(frm.doc[table_field] || []).forEach((row) => {
		qty += flt(row.qty);
		amount += flt(row.amount);
	});

	if (total_qty_field) {
		frm.set_value(total_qty_field, qty);
	}
	if (total_amount_field) {
		frm.set_value(total_amount_field, amount);
	}
};

stockroom.form.update_line_and_totals = function (frm, cdt, cdn, table_field, options) {
	stockroom.form.calc_row_amount(cdt, cdn);
	stockroom.form.calc_parent_totals(frm, table_field, options);
};

stockroom.form.company_filters = function (company, extra = {}) {
	return { company, disabled: 0, ...extra };
};

stockroom.form.setup_company_filters = function (frm, config = {}) {
	const apply = () => {
		const company = frm.doc.company;
		if (!company) return;

		const leaf_wh = stockroom.form.company_filters(company, { is_group: 0 });

		(config.link_fields || []).forEach((fieldname) => {
			frm.set_query(fieldname, () => ({
				filters: stockroom.form.company_filters(company),
			}));
		});

		(config.warehouse_fields || []).forEach((fieldname) => {
			frm.set_query(fieldname, () => ({ filters: leaf_wh }));
		});

		(config.order_fields || []).forEach(({ field, doctype, status }) => {
			frm.set_query(field, () => ({
				filters: {
					company,
					docstatus: 1,
					...(status ? { status } : {}),
				},
			}));
		});

		(config.child_tables || []).forEach(({ table, warehouse_field = "warehouse" }) => {
			frm.set_query(warehouse_field, table, () => ({ filters: leaf_wh }));
		});

		(config.custom || []).forEach(({ field, filters_fn }) => {
			frm.set_query(field, filters_fn);
		});
	};

	frm._stockroom_company_filter = apply;
	apply();
};

stockroom.form.on_company_change = function (frm, fields_to_clear = []) {
	fields_to_clear.forEach((field) => frm.set_value(field, ""));
	if (frm._stockroom_company_filter) {
		frm._stockroom_company_filter();
	}
};
