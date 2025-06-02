frappe.ui.form.on('Item', {
    validate: function(frm) {
        if (frm.doc.custom_has_tolerance && (frm.doc.custom_maximum_weight_per_nos === 0 || frm.doc.custom_standard_weight_per_nos === 0)) {
            frappe.throw('Weight per Nos should be greater than 0');
        }
        if (frm.doc.custom_has_tolerance && (frm.doc.custom_maximum_weight_per_nos < frm.doc.custom_standard_weight_per_nos || frm.doc.custom_standard_weight_per_nos < frm.doc.custom_minimum_weight_per_nos)) {
            frappe.throw('Maximum weight per Nos should be greater than minimum weight per Nos');
        }
    },
});
