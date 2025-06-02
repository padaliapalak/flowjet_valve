frappe.ui.form.on('Opportunity Item', {
    custom_is_new_item(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.custom_is_new_item) {
            frappe.model.set_value(cdt, cdn, 'item_code', null);
            frappe.model.set_value(cdt, cdn, 'item_name', null);
        } else {
            frappe.model.set_value(cdt, cdn, 'custom_new_item', null);
        }
        frm.fields_dict.items.grid.refresh();
    },
});
