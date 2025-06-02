frappe.ui.form.on('Purchase Receipt', {
    after_save: function(frm) {
        if (frm.doc.docstatus === 0) {
            let promises = [];
            // let need_approval = false;
            frm.doc.items.forEach(item => {
                const promise = frappe.db.get_value('Item', item.item_code, ['custom_has_tolerance', 'custom_minimum_weight_per_nos', 'custom_maximum_weight_per_nos']).then(res => {
                    if (res.message.custom_has_tolerance) {
                        const actual_weight_per_nos = item.custom_total_wt / item.qty;
                        if (res.message.custom_minimum_weight_per_nos > actual_weight_per_nos || actual_weight_per_nos > res.message.custom_maximum_weight_per_nos) {
                            frappe.msgprint(`Item ${item.item_code} weight per Nos ${actual_weight_per_nos.toFixed(3)} should be between ${res.message.custom_minimum_weight_per_nos} and ${res.message.custom_maximum_weight_per_nos}`);
                            // need_approval = true;
                            return true; // needs approval
                        }
                    }
                    return false; // doesn't need approval
                });
                promises.push(promise);
            });

            Promise.all(promises).then(results => {
                const need_approval = results.includes(true);
                frappe.db.set_value(frm.doc.doctype, frm.doc.name, 'custom_need_approval', need_approval ? 1 : 0)
        .then(() => {
            frm.reload_doc(); // <- this will fully refresh the form with updated DB values
        });
});
        }
    },
    refresh: function(frm) {
        if (frm.doc.docstatus === 0) {
            frm.doc.items.forEach(item => {
                if (!item.custom_total_wt && item.custom_weight_per_nos) {
                    frappe.model.set_value('Purchase Receipt Item', item.name, "custom_total_wt", item.custom_weight_per_nos * item.qty);
                }
            });
        }
    }
});

frappe.ui.form.on('Purchase Receipt Item', {
    item_code: function(frm, cdt, cdn) {
        var child = locals[cdt][cdn];
        if (frm.doc.docstatus === 0 && !child.custom_total_wt && child.custom_weight_per_nos) {
            frappe.model.set_value(cdt, cdn, "custom_total_wt", child.custom_weight_per_nos * child.qty);
        }
    },
    custom_total_wt: function(frm, cdt, cdn) {
        var child = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, "rate", child.price_list_rate * child.custom_total_wt / child.qty / child.custom_weight_per_nos);
    }
});