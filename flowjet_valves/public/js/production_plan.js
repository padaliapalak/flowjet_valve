frappe.ui.form.on('Production Plan', {
    onload: function(frm) {
        // Define priority order
        const priority_order = ['Urgent', 'High', 'Medium', 'Low'];

        // Sort mr_items table by priority
        frm.doc.mr_items.sort((a, b) => {
            return priority_order.indexOf(a.custom_priority) - priority_order.indexOf(b.custom_priority);
        });

        // Refresh the field to reflect new order
        frm.refresh_field('mr_items');
    },
    refresh(frm) {
        setTimeout(() => {
            // Update custom_priority in sales_orders table
            if (frm.doc.sales_orders && frm.doc.sales_orders.length > 0) {
                frm.doc.sales_orders.forEach(row => {
                    if (row.sales_order) {
                        frappe.db.get_doc('Sales Order', row.sales_order).then(sales_order => {
                            row.custom_priority = sales_order.custom_priority;
                            frm.refresh_field('sales_orders');

                            // Build item_priority_map from Sales Order Items
                            let item_priority_map = {};
                            (sales_order.items || []).forEach(so_item => {
                                if (so_item.item_code && so_item.custom_priority) {
                                    item_priority_map[so_item.item_code] = so_item.custom_priority;
                                }
                            });

                            // Now update po_items based on item_code match
                            (frm.doc.po_items || []).forEach(po_item => {
                                if (item_priority_map[po_item.item_code]) {
                                    po_item.custom_priority = item_priority_map[po_item.item_code];
                                }
                            });

                            frm.refresh_field('po_items');
                        });
                    }
                });
            }
        }, 500);
        frm.page.remove_inner_button('Material Request', 'Create');

		if (frm.doc.docstatus === 1 && frm.doc.status !== 'Completed' && frm.doc.status !== 'Closed') {
            frm.add_custom_button(__('Material Request'), function () {
                // Directly trigger without confirmation
                frm.events.create_material_request(frm, 0);
            }, __('Create'));
        }
    },
    get_items(frm) {
        frm.save();
    }
});
