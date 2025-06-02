frappe.ui.form.on('Sales Order', {
    custom_priority(frm) {
        if (frm.doc.items && frm.doc.custom_priority) {
            // updateProductionPlans(frm);
            frm.doc.items.forEach(row => {
                if (!row.custom_priority) row.custom_priority = frm.doc.custom_priority;
            });
            frm.refresh_field('items');
        }
    },
    after_save(frm) {
        if (frm.doc.docstatus == 1) updateManufactureCycle(frm);
    },
    refresh(frm) {
        if (!frm.doc.selling_price_list) return;

        frm.doc.items.forEach(row => {
            if (!row.item_code) return;

            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Item Price",
                    filters: {
                        item_code: row.item_code,
                        price_list: frm.doc.selling_price_list
                    },
                    fieldname: "price_list_rate"
                },
                callback: function (r) {
                    if (!r.message) return;

                    let price_list_rate = r.message.price_list_rate;
                    if (flt(row.rate) !== flt(price_list_rate)) {
                        $(`[data-idx="${row.idx}"] [data-fieldname="rate"]`).css("color", "red");
                    } else {
                        $(`[data-idx="${row.idx}"] [data-fieldname="rate"]`).css("color", "");
                    }
                }
            });
        });
        if (frm.doc.docstatus == 1) frm.add_custom_button(__('Dispatch Allocation'), function() {
            frappe.call({
                method: "flowjet_valves.public.py.sales_order.get_sales_order_items",
                args: { sales_order: frm.doc.name },
                callback: function (r) {
                    if (!r.message || r.message.length === 0) {
                        frappe.msgprint("No items found in the Sales Order.");
                        return;
                    }

                    let items = r.message.map((item) => ({
                        item_code: item.item_code,
                        item_name: item.item_name,
                        qty: item.qty,
                        name: item.name,
                        warehouse: item.warehouse,
                        // batch_no: item.batch_no,
                        delivery_date: item.delivery_date,
                        actual_qty: item.actual_qty
                    }));
                    console.log("Items:", items);

                    let dialog = new frappe.ui.Dialog({
                        title: __("Create Dispatch Allocation"),
                        fields: [
                            {
                                fieldtype: "Data",
                                fieldname: "selected_count",
                                label: "Selected Items Count",
                                default: 0,
                                read_only: 1,
                            },
                            {
                                fieldtype: "Table",
                                fieldname: "item_table",
                                label: "Items",
                                cannot_add_rows: true,
                                cannot_delete_all_rows: true,
                                fields: [
                                    {
                                        fieldtype: "Data",
                                        fieldname: "item_code",
                                        label: "Item Code",
                                        read_only: 1,
                                        in_list_view: 1,
                                        columns: 2,
                                    },
                                    {
                                        fieldtype: "Float",
                                        fieldname: "qty",
                                        label: "Required Qty",
                                        read_only: 1,
                                        in_list_view: 1,
                                        columns: 1,
                                    },
                                    {
                                        fieldtype: "Float",
                                        fieldname: "allocated_qty",
                                        label: "Allocated Qty",
                                        read_only: 0,
                                        in_list_view: 1,
                                        columns: 1,
                                    },
                                    {
                                        fieldtype: "Float",
                                        fieldname: "actual_qty",
                                        label: "Available Qty",
                                        read_only: 1,
                                        in_list_view: 1,
                                        columns: 1,
                                    },
                                    {
                                        fieldtype: "Link",
                                        fieldname: "warehouse",
                                        label: "Warehouse",
                                        options: "Warehouse",
                                        read_only: 1,
                                        in_list_view: 1,
                                        columns: 2,
                                    },
                                    {
                                        fieldtype: "Link",
                                        fieldname: "batch_no",
                                        label: "Batch No.",
                                        options: "Batch",
                                        read_only: 1,
                                        in_list_view: 1,
                                        columns: 1,
                                    },
                                    {
                                        fieldtype: "Date",
                                        fieldname: "delivery_date",
                                        label: "Expected Dispatch Date",
                                        read_only: 1,
                                        in_list_view: 1,
                                        columns: 1,
                                    },
                                    {
                                        fieldtype: "Data",
                                        fieldname: "item_name",
                                        label: "Item Name",
                                        read_only: 1,
                                        columns: 3,
                                    },
                                ],
                            },
                        ],
                        primary_action_label: __("Create"),
                        primary_action(values) {
                        let selected_items = dialog.fields_dict.item_table.grid.get_selected_children();
                        if (!selected_items.length) {
                            frappe.msgprint("Please select at least one item.");
                            return;
                        }

                            dialog.hide();
                            frappe.model.open_mapped_doc({
                                method: "erpnext.selling.doctype.sales_order.sales_order.make_delivery_note",
                                frm: frm,
                                args: {
                                    // supplier: values.supplier, // pass selected supplier
                                    filtered_children: selected_items.map((row) => row.name), // pass only selected items
                                },
                                run_link_triggers: true,
                            });
                        },
                        // Add a custom class
                        wrapper_class: "wide-dispatch-dialog"
                    });

                    // Fill and show dialog
                    dialog.fields_dict.item_table.df.data = items;
                    dialog.fields_dict.item_table.grid.grid_pagination.page_length = 10;
                    dialog.fields_dict.item_table.grid.refresh();
                    dialog.show();
                    dialog.$wrapper.find(".modal-content").css("width", "250%");
                    dialog.$wrapper.find(".modal-dialog").css("margin", "1.75rem 17.5rem");

                // Count updater function
                function updateSelectedCount() {
                    let count = dialog.fields_dict.item_table.grid.get_selected().length;
                    dialog.set_value("selected_count", count);
                    dialog.refresh_field("selected_count");
                }

                // Bind event listener to track selection changes
                dialog.fields_dict.item_table.grid.wrapper.on('click', '.grid-row-check', function() {
                    setTimeout(() => {
                        updateSelectedCount();
                    }, 50);
                });

                // Initial update count
                setTimeout(() => {
                    updateSelectedCount();
                }, 100);
                }
            });
        }, __('Make'));
    },
});


frappe.ui.form.on('Sales Order Item', {
    rate(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.item_code || !frm.doc.selling_price_list) return;

        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "Item Price",
                filters: {
                    item_code: row.item_code,
                    price_list: frm.doc.selling_price_list
                },
                fieldname: "price_list_rate"
            },
            callback: function (r) {
                if (!r.message) return;

                let price_list_rate = r.message.price_list_rate;
                // Compare the rate
                if (price_list_rate && (flt(row.rate) !== flt(price_list_rate))) {
                    // Apply red style to the 'rate' field
                    $(`[data-idx="${row.idx}"] [data-fieldname="rate"]`).css("color", "red");
                } else {
                    // Reset color if it's the same
                    $(`[data-idx="${row.idx}"] [data-fieldname="rate"]`).css("color", "");
                }
            }
        });
    }
});


function updateManufactureCycle(frm) {
    let item_priority_map = {};

    (frm.doc.items || []).forEach(item => {
        if (item.item_code) {
            item_priority_map[item.item_code] = item.custom_priority;
        }
    });

    frm.call({
        method: 'flowjet_valves.public.py.sales_order.update_manufacture_cycle',
        args: {
            name: frm.doc.name,
            custom_priority: frm.doc.custom_priority,
            item_priority_map: item_priority_map
        }
    });
}