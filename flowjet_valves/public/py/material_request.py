import frappe
from erpnext.stock.doctype.item.item import get_item_defaults

def copy_custom_fields(doc, method):

    for item in doc.items:
        if not item.production_plan:
            return
        
        plan_item = frappe.db.get_value(
            "Material Request Plan Item",
            {
                "parent": item.production_plan,
                "item_code": item.item_code,
                "warehouse": item.warehouse,
            },
            ["custom_remarks", "custom_priority"],
            as_dict=True
        )
        if plan_item and plan_item.custom_remarks:
            item.custom_remarks = plan_item.custom_remarks

        if plan_item and plan_item.custom_priority:
            item.custom_priority = plan_item.custom_priority


# @frappe.whitelist()
# def create_purchase_orders_by_custom_supplier(material_request):
# 	mr = frappe.get_doc("Material Request", material_request)

# 	if mr.get("custom_po_created"):
# 		frappe.throw("Purchase Orders have already been created for this Material Request.")

# 	supplier_items_map = {}

# 	# Group items by custom_suggested_supplier
# 	for item in mr.items:
# 		supplier = item.custom_suggested_supplier
# 		if not supplier:
# 			continue
# 		supplier_items_map.setdefault(supplier, []).append(item)

# 	created_pos = []

# 	for supplier, items in supplier_items_map.items():
# 		po = frappe.new_doc("Purchase Order")
# 		po.supplier = supplier
# 		po.set("items", [])

# 		for d in items:
# 			po.append("items", {
# 				"item_code": d.item_code,
# 				"qty": d.qty,
# 				"uom": d.uom,
# 				"warehouse": d.warehouse,
# 				"schedule_date": d.schedule_date,
# 				"material_request": mr.name,
# 				"material_request_item": d.name,
# 			})

# 		po.set_missing_values()
# 		po.insert()
# 		created_pos.append(po.name)

# 	# Mark MR as PO Created
# 	mr.db_set("custom_po_created", 1)

# 	return created_pos


@frappe.whitelist()
def get_material_request_items_with_supplier(material_request):
    items = frappe.get_all(
        "Material Request Item",
        filters={"parent": material_request},
        fields=["name", "item_code", "item_name", "qty"]
    )
    filtered_items = []

    for item in items:
        submitted_po = frappe.db.sql("""
            SELECT SUM(qty) FROM `tabPurchase Order Item`
            WHERE material_request_item = %s AND docstatus = 1
        """, item.name)[0][0] or 0
        remaining_qty = item.qty - submitted_po

        # Set the submitted PO qty into custom_pending_for_po_qty
        frappe.db.set_value("Material Request Item", item.name, "custom_pending_for_po_qty", remaining_qty)
        if remaining_qty <= 0:
            continue
        item["qty"] = remaining_qty

        item_defaults = get_item_defaults(
            item.item_code,
            frappe.db.get_value("Material Request", material_request, "company")
        )
        item["supplier"] = item_defaults.get("default_supplier")
        filtered_items.append(item)

    return filtered_items