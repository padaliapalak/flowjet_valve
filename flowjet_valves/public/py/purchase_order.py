import frappe
from frappe.model.mapper import get_mapped_doc
from erpnext.buying.doctype.purchase_order.purchase_order import set_missing_values


@frappe.whitelist()
def update_item_history(po_name, items_data):
    doc = frappe.get_doc("Purchase Order", po_name)

    # Allow changes to submitted doc
    doc.ignore_submit = True

    doc.append("custom_items_history", {
        "date": frappe.utils.now_datetime(),
        "user": frappe.session.user,
        "details": items_data
    })

    doc.save()
    return "Items Updated successfully"


@frappe.whitelist()
def make_new_po_from_remaining(source_name):
    def update_item(source_doc, target_doc, source_parent):
        # Only include items with remaining qty
        qty_diff = source_doc.qty - source_doc.received_qty
        if qty_diff > 0:
            target_doc.qty = qty_diff
            target_doc.schedule_date = source_doc.schedule_date
        else:
            target_doc.idx = None  # this will be dropped

    doc = get_mapped_doc(
        "Purchase Order",
        source_name,
        {
            "Purchase Order": {
                "doctype": "Purchase Order",
                "field_map": {
                    "supplier": "supplier",
                    "schedule_date": "schedule_date"
                },
                "validation": {"docstatus": ["=", 1]}
            },
            "Purchase Order Item": {
                "doctype": "Purchase Order Item",
                "field_map": {
                    "name": "prevdoc_detail_docname",
                    "parent": "prevdoc_docname"
                },
                "condition": lambda d: d.qty > d.received_qty,
                "postprocess": update_item,
            }
        },
        target_doc=None,
        postprocess=set_missing_values
    )
    doc.supplier = ''
    doc.supplier_name = ''

    return doc
