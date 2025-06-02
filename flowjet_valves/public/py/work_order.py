import frappe
from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder
from frappe.utils import (cint, flt)
from frappe import _


@frappe.whitelist()
def get_custom_priority_from_pp_items(item_type, item_name):
    if item_type == "main":
        return frappe.db.get_value('Production Plan Item', item_name, 'custom_priority')
    
    elif item_type == "sub":
        # Get parent item code from sub-assembly item
        parent_item_code = frappe.db.get_value('Production Plan Sub Assembly Item', item_name, 'parent_item_code')

        if not parent_item_code:
            return None

        # Now get custom_priority from the Production Plan Item with matching item_code
        result = frappe.db.get_value('Production Plan Item', {'item_code': parent_item_code}, 'custom_priority')
        return result

    return None


@frappe.whitelist()
def get_excluded_work_orders():
    # Get all finished Work Orders (for finished goods)
    finished_wos = frappe.get_all("Work Order", filters={
        "docstatus": ["<", 2],
        "production_plan_item": ["!=", ""]
    }, fields=["name", "production_plan", "production_plan_item"])

    excluded_wo_names = []

    for wo in finished_wos:
        # Get related sub-assembly rows from Production Plan
        sub_assembly_links = frappe.get_all(
            "Production Plan Sub Assembly Item",
            filters={
                "parent": wo.production_plan,
                "production_plan_item": wo.production_plan_item
            },
            fields=["name"]
        )

        if not sub_assembly_links:
            # No sub-assemblies → allow (don't exclude)
            continue

        # Get statuses of Work Orders linked to these sub_assembly_items
        sub_assembly_wos = frappe.get_all(
            "Work Order",
            filters={
                "production_plan_sub_assembly_item": ["in", [row.name for row in sub_assembly_links]]
            },
            fields=["status"]
        )

        if any(s.status != "Completed" for s in sub_assembly_wos):
            # If any sub-assembly is NOT completed → EXCLUDE this finished WO
            excluded_wo_names.append(wo.name)

    return excluded_wo_names



class CustomWorkOrder(WorkOrder):
    def validate_qty(self):
        # OVERRIDDEN: Don't throw error for qty <= 0
        if (
            self.stock_uom
            and frappe.get_cached_value("UOM", self.stock_uom, "must_be_whole_number")
            and abs(cint(self.qty) - flt(self.qty, self.precision("qty"))) > 0.0000001
        ):
            frappe.throw(
                _(
                    "Qty To Manufacture ({0}) cannot be a fraction for the UOM {2}. To allow this, disable '{1}' in the UOM {2}."
                ).format(
                    flt(self.qty, self.precision("qty")),
                    frappe.bold(_("Must be Whole Number")),
                    frappe.bold(self.stock_uom),
                ),
            )

        # Keep the rest of the logic
        if self.production_plan and self.production_plan_item and not self.production_plan_sub_assembly_item:
            qty_dict = frappe.db.get_value(
                "Production Plan Item", self.production_plan_item, ["planned_qty", "ordered_qty"], as_dict=1
            )

            if not qty_dict:
                return

            allowance_qty = (
                flt(
                    frappe.db.get_single_value(
                        "Manufacturing Settings", "overproduction_percentage_for_work_order"
                    )
                )
                / 100
                * qty_dict.get("planned_qty", 0)
            )

            max_qty = qty_dict.get("planned_qty", 0) + allowance_qty - qty_dict.get("ordered_qty", 0)

            if not max_qty > 0:
                frappe.throw(
                    _("Cannot produce more item for {0}").format(self.production_item)
                )
            elif self.qty > max_qty:
                frappe.throw(
                    _("Cannot produce more than {0} items for {1}").format(max_qty, self.production_item)
                )
