frappe.ui.form.on('Quotation Item', {
    item_code(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (row.item_code && frm.doc.party_name) {
            frappe.call({
                method: 'flowjet_valves.public.py.quotation.get_last_item_rate',
                args: {
                    party_name: frm.doc.party_name,
                    item_code: row.item_code
                },
                callback(r) {
                    frappe.model.set_value(cdt, cdn, 'custom_previous_rate', r.message/frm.doc.conversion_rate || 0);
                }
            });
        }
    }
});