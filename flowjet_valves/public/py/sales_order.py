import frappe
import json
from flowjet_valves.public.py.production_plan import get_items_for_material_requests
from erpnext.stock.doctype.item.item import get_item_defaults

@frappe.whitelist()
def update_manufacture_cycle(name, custom_priority=None, item_priority_map=None):
    if isinstance(item_priority_map, str):
        item_priority_map = json.loads(item_priority_map)

    # Step 1: Get related Production Plans from Sales Order
    production_plans = frappe.get_all(
        "Production Plan Sales Order",
        filters={"sales_order": name},
        fields=["parent"]
    )

    for plan in production_plans:
        production_plan = frappe.get_doc("Production Plan", plan.parent)
        
        # Skip cancelled Production Plans
        if production_plan.docstatus == 2:
            continue

        # Step 2: Update priority in Production Plan Sales Order table
        for row in production_plan.sales_orders:
            if row.sales_order == name:
                row.custom_priority = custom_priority

        # Step 3: Update custom_priority in Production Plan Item table
        for item in production_plan.po_items:
            if item.item_code in item_priority_map:
                item.custom_priority = item_priority_map[item.item_code]

                work_orders = frappe.get_list("Work Order", filters={"production_plan_item": item.name}, pluck="name")
                for wo_name in work_orders:
                    work_order = frappe.get_doc("Work Order", wo_name)
                    work_order.custom_priority = item.custom_priority
                    work_order.save(ignore_permissions=True)

                    job_cards = frappe.get_list("Job Card", filters={"work_order": wo_name}, pluck="name")
                    for jc_name in job_cards:
                        frappe.db.set_value("Job Card", jc_name, "custom_priority", item.custom_priority)


        # Step 4: Update custom_priority in Production Plan Sub Assembly Item table
        for item in production_plan.sub_assembly_items:
            if item.parent_item_code in item_priority_map:

                work_order_sub_assemblies = frappe.get_list("Work Order", filters={"production_plan_sub_assembly_item": item.name}, pluck="name")
                for wo_name in work_order_sub_assemblies:
                    work_order = frappe.get_doc("Work Order", wo_name)
                    work_order.custom_priority = item_priority_map[item.parent_item_code]
                    work_order.save(ignore_permissions=True)

                    job_cards = frappe.get_list("Job Card", filters={"work_order": wo_name}, pluck="name")
                    for jc_name in job_cards:
                        frappe.db.set_value("Job Card", jc_name, "custom_priority", item_priority_map[item.parent_item_code])

        production_plan.save(ignore_permissions=True)

        # Step 5: Update Material Request priorities via MR item generation
        items = get_items_for_material_requests(production_plan.as_dict())

        for item in items:
            item_code = item.get("item_code")
            priority = item.get("custom_priority")

            # Find matching Material Request Plan Item rows (you can narrow down further using production_plan or company if needed)
            mr_items = frappe.get_all(
                "Material Request Plan Item",
                filters={
                    "item_code": item_code,
                    "parent": production_plan.name
                },
                fields=["name"]
            )

            for mr_item in mr_items:
                frappe.db.set_value("Material Request Plan Item", mr_item.name, "custom_priority", priority)


@frappe.whitelist()
def get_sales_order_items(sales_order):
    items = frappe.get_all(
        "Sales Order Item",
        filters={"parent": sales_order},
        fields=["name", "item_code", "item_name", "qty", "warehouse", "delivery_date", "actual_qty"]
    )

    # filtered_items = []

    # for item in items:
    #     submitted_dn = frappe.db.sql("""
    #         SELECT SUM(qty) FROM `tabDelivery Note Item`
    #         WHERE sales_order_item = %s AND docstatus = 1
    #     """, item.name)[0][0] or 0

    #     remaining_qty = item.qty - submitted_dn

    #     # Set the submitted PO qty into custom_pending_for_po_qty
    #     frappe.db.set_value("Sales Order Item", item.name, "custom_pending_for_po_qty", remaining_qty)

    #     if remaining_qty <= 0:
    #         continue

    #     item["qty"] = remaining_qty

    #     item_defaults = get_item_defaults(
    #         item.item_code,
    #         frappe.db.get_value("Sales Order", sales_order, "company")
    #     )
    #     item["supplier"] = item_defaults.get("default_supplier")

    #     filtered_items.append(item)

    # return filtered_items
    return items