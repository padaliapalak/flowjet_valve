__version__ = "1.0.0"

import frappe
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.stock.doctype.material_request.material_request import set_missing_values, update_item
import erpnext.stock.doctype.material_request.material_request as MaterialRequest
from frappe.model.mapper import get_mapped_doc
import erpnext.selling.doctype.sales_order.sales_order as sales_order_module
from erpnext.stock.doctype.packed_item.packed_item import make_packing_list
from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
    get_sre_details_for_voucher,
    get_sre_reserved_qty_details_for_voucher,
    get_ssb_bundle_for_voucher,
)
from erpnext.stock.doctype.delivery_note.delivery_note import get_company_address
from frappe.model.utils import get_fetch_values
from erpnext.stock.get_item_details import get_item_defaults, get_item_group_defaults
from frappe.utils import flt, cstr


@frappe.whitelist()
def custom_make_purchase_order(source_name, target_doc=None, args=None, supplier=None, filtered_children=None):
    # Step 1: Normalize args
    if args is None and hasattr(frappe.flags, "args"):
        args = frappe.flags.args
    if isinstance(args, str):
        import json
        args = json.loads(args)
    filtered_items = args.get("filtered_children", []) if args else []
	
    def postprocess(source, target_doc):
        if args.get("supplier"):
            target_doc.supplier = args["supplier"]
        set_missing_values(source, target_doc)

    def select_item(d):
        child_filter = d.name in filtered_items if filtered_items else True
        qty = d.received_qty or d.ordered_qty
        return qty < d.stock_qty and child_filter

    doclist = get_mapped_doc(
        "Material Request",
        source_name,
        {
            "Material Request": {
                "doctype": "Purchase Order",
                "validation": {
                    "docstatus": ["=", 1],
                    "material_request_type": ["=", "Purchase"],
                },
            },
            "Material Request Item": {
                "doctype": "Purchase Order Item",
                "field_map": [
                    ["name", "material_request_item"],
                    ["parent", "material_request"],
                    ["uom", "stock_uom"],
                    ["uom", "uom"],
                    ["sales_order", "sales_order"],
                    ["sales_order_item", "sales_order_item"],
                    ["wip_composite_asset", "wip_composite_asset"],
                ],
                "postprocess": update_item,
                "condition": select_item,
            },
        },
        target_doc,
        postprocess,
    )

    doclist.set_onload("load_after_mapping", False)
    return doclist

MaterialRequest.make_purchase_order = custom_make_purchase_order



@frappe.whitelist()
def custom_make_delivery_note(source_name, target_doc=None, kwargs=None):
	# Normalize kwargs
	if kwargs is None and hasattr(frappe.flags, "args"):
		kwargs = frappe.flags.args
	if isinstance(kwargs, str):
		import json
		kwargs = json.loads(kwargs)

	kwargs = frappe._dict(kwargs)

	filtered_items = kwargs.get("filtered_children", []) if kwargs else []
	sre_details = {}

	if kwargs.for_reserved_stock:
		sre_details = get_sre_reserved_qty_details_for_voucher("Sales Order", source_name)

	mapper = {
		"Sales Order": {"doctype": "Delivery Note", "validation": {"docstatus": ["=", 1]}},
		"Sales Taxes and Charges": {"doctype": "Sales Taxes and Charges", "reset_value": True},
		"Sales Team": {"doctype": "Sales Team", "add_if_empty": True},
	}

	def set_missing_values(source, target):
		if kwargs.get("ignore_pricing_rule"):
			target.ignore_pricing_rule = 1

		target.run_method("set_missing_values")
		target.run_method("set_po_nos")
		target.run_method("calculate_taxes_and_totals")
		target.run_method("set_use_serial_batch_fields")

		if source.company_address:
			target.company_address = source.company_address
		else:
			target.update(get_company_address(target.company))

		if target.company_address:
			target.update(get_fetch_values("Delivery Note", "company_address", target.company_address))

		if frappe.flags.bulk_transaction:
			target.set_new_name()

		make_packing_list(target)

	def condition(doc):
		if doc.name in sre_details:
			del sre_details[doc.name]
			return False

		if frappe.flags.args and frappe.flags.args.delivery_dates:
			if cstr(doc.delivery_date) not in frappe.flags.args.delivery_dates:
				return False

		child_match = doc.name in filtered_items if filtered_items else True
		return abs(doc.delivered_qty) < abs(doc.qty) and doc.delivered_by_supplier != 1 and child_match

	def update_item(source, target, source_parent):
		target.base_amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.base_rate)
		target.amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.rate)
		target.qty = flt(source.qty) - flt(source.delivered_qty)

		item = get_item_defaults(target.item_code, source_parent.company)
		item_group = get_item_group_defaults(target.item_code, source_parent.company)

		if item:
			target.cost_center = (
				frappe.db.get_value("Project", source_parent.project, "cost_center")
				or item.get("buying_cost_center")
				or item_group.get("buying_cost_center")
			)

	if not kwargs.skip_item_mapping:
		mapper["Sales Order Item"] = {
			"doctype": "Delivery Note Item",
			"field_map": {
				"rate": "rate",
				"name": "so_detail",
				"parent": "against_sales_order",
			},
			"condition": condition,
			"postprocess": update_item,
		}

	so = frappe.get_doc("Sales Order", source_name)
	target_doc = get_mapped_doc("Sales Order", so.name, mapper, target_doc)

	# Handle reserved stock
	if not kwargs.skip_item_mapping and kwargs.for_reserved_stock:
		sre_list = get_sre_details_for_voucher("Sales Order", source_name)
		if sre_list:
			def update_dn_item(source, target, source_parent):
				update_item(source, target, so)

			so_items = {d.name: d for d in so.items if d.stock_reserved_qty}
			for sre in sre_list:
				if not condition(so_items[sre.voucher_detail_no]):
					continue

				dn_item = get_mapped_doc(
					"Sales Order Item",
					sre.voucher_detail_no,
					{
						"Sales Order Item": {
							"doctype": "Delivery Note Item",
							"field_map": {
								"rate": "rate",
								"name": "so_detail",
								"parent": "against_sales_order",
							},
							"postprocess": update_dn_item,
						}
					},
					ignore_permissions=True,
				)

				dn_item.qty = flt(sre.reserved_qty) / flt(dn_item.get("conversion_factor", 1))

				if sre.reservation_based_on == "Serial and Batch" and (sre.has_serial_no or sre.has_batch_no):
					dn_item.serial_and_batch_bundle = get_ssb_bundle_for_voucher(sre)

				target_doc.append("items", dn_item)

			# Correct row index
			for idx, item in enumerate(target_doc.items):
				item.idx = idx + 1

	set_missing_values(so, target_doc)
	return target_doc

# Patch the default ERPNext function
sales_order_module.make_delivery_note = custom_make_delivery_note
