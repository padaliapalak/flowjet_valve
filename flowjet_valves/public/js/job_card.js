frappe.ui.form.on('Job Card', {
    refresh: function(frm) {
        if (frm.doc.docstatus == 0 && frm.doc.custom_job_type != 'Sub Contract') {
            frm.add_custom_button(__('Sub Contract'), function() {
                frappe.prompt([
                    {
                        label: 'Job Type',
                        fieldname: 'custom_job_type',
                        fieldtype: 'Read Only',
                        default: 'Sub Contract',
                    },
                    {
                        label: 'Qty To Sub-Contract',
                        fieldname: 'custom_qty_to_subcontract',
                        fieldtype: 'Float',
                        reqd: 1,
                        depends_on: "eval:doc.custom_job_type === 'Sub Contract'",
                        description: frm.doc.total_completed_qty !== 0
                            ? 'Total Qty To Manufacture: ' + frm.doc.process_loss_qty
                            : 'Total Qty To Manufacture: ' + frm.doc.for_quantity
                    },
                ], function(values) {
                    // Check required condition manually
                    let max_qty = frm.doc.total_completed_qty !== 0 ? frm.doc.process_loss_qty : frm.doc.for_quantity;
                    if (values.custom_job_type === 'Sub Contract' && (!values.custom_qty_to_subcontract || 0 > values.custom_qty_to_subcontract || values.custom_qty_to_subcontract > max_qty)) {
                        frappe.msgprint(__('Please enter a valid quantity'));
                        return;
                    }
                    frm.set_value('custom_job_type', 'Sub Contract');
                    frm.set_value('custom_qty_to_subcontract', values.custom_qty_to_subcontract);
                    frm.save();
                }, 'Select Job Type', 'Set');
            }, __('Make Job Type to'));
        }

        // if (frm.doc.docstatus == 0 && !frm.doc.custom_job_type) {
        //     frappe.prompt([
        //         {
        //             label: 'Job Type',
        //             fieldname: 'custom_job_type',
        //             fieldtype: 'Select',
        //             options: ['In-house', 'Sub Contract'],
        //             reqd: 1
        //         },
        //         {
        //             label: 'Qty To Sub-Contract',
        //             fieldname: 'custom_qty_to_subcontract',
        //             fieldtype: 'Float',
        //             depends_on: "eval:doc.custom_job_type === 'Sub Contract'",
        //             description: frm.doc.total_completed_qty !== 0
        //                 ? 'Total Qty To Manufacture: ' + frm.doc.process_loss_qty
        //                 : 'Total Qty To Manufacture: ' + frm.doc.for_quantity
        //         },
        //     ], function(values) {
        //         // Check required condition manually
        //         let max_qty = frm.doc.total_completed_qty !== 0 ? frm.doc.process_loss_qty : frm.doc.for_quantity;
        //         if (values.custom_job_type === 'Sub Contract' && (!values.custom_qty_to_subcontract || 0 > values.custom_qty_to_subcontract || values.custom_qty_to_subcontract > max_qty)) {
        //             frappe.msgprint(__('Please enter a valid quantity'));
        //             return;
        //         }
                
        //         frm.set_value('custom_job_type', values.custom_job_type);
                
        //         if (values.custom_job_type === 'Sub Contract') {
        //             frm.set_value('custom_qty_to_subcontract', values.custom_qty_to_subcontract);
        //             frm.set_value('for_quantity', frm.doc.for_quantity - values.custom_qty_to_subcontract);
        //         }
                
        //         frm.save(); // Save the form
        //     }, 'Select Job Type', 'Set');
        // }
        
        if (frm.doc.docstatus == 0 && frm.doc.custom_job_type === 'Sub Contract' && frm.doc.for_quantity !== frm.doc.total_completed_qty) {            
            frm.add_custom_button(__('Sub Contract PO'), function() {
                // Step 1: Fetch operation document
                frappe.db.get_doc('Operation', frm.doc.operation).then(operation_doc => {
                    const service_item = operation_doc.custom_sub_contract_service_item;
                    // const contract_supplier = operation_doc.custom_sub_contract_supplier;
    
                    
                    // Step 2: Prompt for supplier
                    frappe.prompt([
                        // {
                        //     label: 'Job Type',
                        //     fieldname: 'custom_job_type',
                        //     fieldtype: 'Read Only',
                        //     default: 'Sub Contract',
                        // },
                        {
                            label: 'Sub-Contracting Supplier',
                            fieldname: 'supplier',
                            fieldtype: 'Link',
                            options: 'Supplier',
                            reqd: 1,
                            // depends_on: "eval:doc.custom_job_type === 'Sub Contract'",
                            // description: frm.doc.total_completed_qty !== 0
                            //     ? 'Total Qty To Manufacture: ' + frm.doc.process_loss_qty
                            //     : 'Total Qty To Manufacture: ' + frm.doc.for_quantity
                        },
                    ], function(values) {
                        // Check required condition manually
                        let supplier = values.supplier;
                        const finished_good = frm.doc.production_item;
        
                        // Step 3: Create Purchase Order
                        frappe.call({
                            method: "frappe.client.insert",
                            args: {
                                doc: {
                                    doctype: "Purchase Order",
                                    is_subcontracted: 1,
                                    supplier: supplier,
                                    schedule_date: frappe.datetime.nowdate(),
                                    items: [
                                        {
                                            item_code: service_item,
                                            fg_item: finished_good,
                                            qty: frm.doc.custom_qty_to_subcontract - frm.doc.custom_po_qty,
                                            fg_item_qty: frm.doc.custom_qty_to_subcontract - frm.doc.custom_po_qty,
                                            warehouse: frm.doc.wip_warehouse || "",
                                            conversion_factor: 1,
                                            uom: frm.doc.uom || "Nos"
                                        }
                                    ]
                                }
                            },
                            callback: function (r) {
                                if (!r.exc) {
                                    const po_name = r.message.name;
        
                                    // Step 3: Add to child table and refresh
                                    let row = frm.add_child("custom_subcontract_details");
                                    row.subcontract_po = po_name;
        
                                    frm.refresh_field("custom_subcontract_details");
                                    frm.save();
        
                                    // Navigate to PO
                                    frappe.set_route("Form", "Purchase Order", po_name);
        
                                }
                            }
                        });
                    }, 'Select Supplier', 'Set');
                });
            }, __('Create'));

            // frm.add_custom_button(__('Sub Contract PO'), function() {
            //     let po = frappe.model.get_new_doc('Purchase Order');

            //     po.is_subcontracted = 1;
            //     po.company = frm.doc.company;
            //     // po.supplier = ""; // leave blank, user will select
            //     po.transaction_date = frappe.datetime.nowdate();

            //     po.items = [{
            //         item_code: "RM Sub Contract service",
            //         fg_item: "RM Sub Contract Finished",
            //         qty: frm.doc.custom_qty_to_subcontract,
            //         fg_item_qty: frm.doc.custom_qty_to_subcontract,
            //         warehouse: frm.doc.wip_warehouse || "",
            //         conversion_factor: 1,
            //         uom: frm.doc.uom || "Nos"
            //     }];

            //     frappe.model.with_doc("Purchase Order", po.name, function() {
            //         frappe.set_route("Form", "Purchase Order", po.name);
            //     });
            // }, __('Create'));

            if (frm.doc.custom_subcontract_details && frm.doc.custom_subcontract_details.length) {
                let promises = frm.doc.custom_subcontract_details.map(sc => {
                    if (sc.subcontract_po) {
                        return frappe.db.get_value('Purchase Order', sc.subcontract_po, ['docstatus', 'total_qty', 'per_received'])
                            .then(res => {
                                if (res.message && res.message.docstatus == 1) {
                                    sc.po_qty = res.message.total_qty;
                                    sc.received_qty = res.message.per_received / 100 * sc.po_qty;
                                    return {
                                        po_qty: sc.po_qty,
                                        received_qty: sc.received_qty
                                    };
                                }
                                return { po_qty: 0, received_qty: 0 };
                            });
                    } else {
                        return Promise.resolve({ po_qty: 0, received_qty: 0 });
                    }
                });

                Promise.all(promises).then(results => {
                    let total_po_qty = 0;
                    let total_received_qty = 0;

                    results.forEach(r => {
                        total_po_qty += r.po_qty;
                        total_received_qty += r.received_qty;
                    });

                    frm.set_value('custom_po_qty', total_po_qty);
                    frm.set_value('custom_received_qty', total_received_qty);
                    // frm.set_value('process_loss_qty', flt(frm.doc.for_quantity, 3) - flt(frm.doc.total_completed_qty, 3) - flt(total_received_qty, 3));

                    frm.refresh_field('custom_subcontract_details');
                    frm.save();
                });
            }


            // if (frm.doc.custom_subcontract_po) {
            //     frappe.db.get_value('Purchase Order', frm.doc.custom_subcontract_po, ['docstatus', 'total_qty','per_received']).then(res => {
            //         if (res.message.docstatus == 1) {
            //             frm.set_value('custom_po_qty', res.message.total_qty);
            //             frm.set_value('custom_received_qty', res.message.per_received/100*frm.doc.custom_po_qty);
            //             frm.set_value('process_loss_qty', flt(frm.doc.for_quantity, 3) - flt(frm.doc.total_completed_qty, 3) - flt(frm.doc.custom_received_qty, 3));
            //         }
            //     })
            // }
        }
    },
    validate : function (frm) {
        // let max_qty = frm.doc.total_completed_qty !== 0 ? frm.doc.process_loss_qty : frm.doc.for_quantity;
        if (frm.doc.custom_qty_to_subcontract && (frm.doc.custom_qty_to_subcontract < frm.doc.custom_po_qty || frm.doc.custom_qty_to_subcontract > frm.doc.custom_po_qty + frm.doc.for_quantity - frm.doc.total_completed_qty)) {
            frappe.throw(__('Subcontracted quantity must be between ' + frm.doc.custom_po_qty + ' and ' + (frm.doc.custom_po_qty + frm.doc.for_quantity - frm.doc.total_completed_qty)));
        }
    },
});

frappe.ui.form.on('Job Card Time Log', {
    completed_qty: function (frm, cdt, cdn) {
        frm.set_value('custom_total_completed_inhouse_qty', flt(frm.doc.total_completed_qty, 3));
        frm.set_value('total_completed_qty', flt(frm.doc.total_completed_qty, 3) + flt(frm.doc.custom_received_qty, 3));
        frm.set_value('process_loss_qty', flt(frm.doc.for_quantity, 3) - flt(frm.doc.total_completed_qty, 3));
    }
});