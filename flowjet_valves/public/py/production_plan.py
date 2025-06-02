import frappe
from collections import defaultdict
from erpnext.manufacturing.doctype.production_plan.production_plan import get_sales_orders as original_get_sales_orders
from frappe.utils import (
	add_days,
	ceil,
	cint,
	comma_and,
	flt,
	get_link_to_form,
	getdate,
	now_datetime,
	nowdate,
)

@frappe.whitelist()
def custom_get_sales_orders(**kwargs):
    sales_orders = original_get_sales_orders(**kwargs)

    for so in sales_orders:
        sales_order_doc = frappe.get_doc("Sales Order", so["sales_order"])
        so["priority"] = sales_order_doc.priority or ""

    return sales_orders





from erpnext.manufacturing.doctype.production_plan.production_plan import ProductionPlan as BasePlan
from frappe import _, msgprint
import frappe

class CustomProductionPlan(BasePlan):
    @frappe.whitelist()
    def make_work_order(self):
        from erpnext.manufacturing.doctype.work_order.work_order import get_default_warehouse

        wo_list, po_list = [], []
        subcontracted_po = {}
        default_warehouses = get_default_warehouse()

        self.make_work_order_for_finished_goods(wo_list, default_warehouses)
        self.make_work_order_for_subassembly_items(wo_list, subcontracted_po, default_warehouses)
        self.make_subcontracted_purchase_order(subcontracted_po, po_list)
        self.show_list_created_message("Work Order", wo_list)
        self.show_list_created_message("Purchase Order", po_list)

        if not wo_list:
            frappe.msgprint(_("Work Order(s) already exists in draft state for these items."))

    def make_work_order_for_finished_goods(self, wo_list, default_warehouses):
        items_data = self.get_production_items()
        for _key, item in items_data.items():
            if self.sub_assembly_items:
                item["use_multi_level_bom"] = 0

            # ✅ Skip if draft WO exists
            if frappe.db.exists(
                "Work Order",
                {
                    "production_plan": self.name,
                    "production_plan_item": item.get("production_plan_item"),
                    "docstatus": 0,
                },
            ):
                continue

            from erpnext.manufacturing.doctype.production_plan.production_plan import set_default_warehouses
            set_default_warehouses(item, default_warehouses)

            work_order = self.create_work_order(item)
            if work_order:
                wo_list.append(work_order)

    def make_work_order_for_subassembly_items(self, wo_list, subcontracted_po, default_warehouses):
        for row in self.sub_assembly_items:
            if row.type_of_manufacturing == "Subcontract":
                subcontracted_po.setdefault(row.supplier, []).append(row)
                continue

            if row.type_of_manufacturing == "Material Request":
                continue

            # ✅ Skip if draft WO already exists
            if frappe.db.exists(
                "Work Order",
                {
                    "production_plan": self.name,
                    "production_plan_sub_assembly_item": row.name,
                    "docstatus": ["in", [0, 1]],
                },
            ):
                continue

            work_order_data = {
                "wip_warehouse": default_warehouses.get("wip_warehouse"),
                "fg_warehouse": default_warehouses.get("fg_warehouse"),
                "company": self.get("company"),
            }

            self.prepare_data_for_sub_assembly_items(row, work_order_data)
            work_order = self.create_work_order(work_order_data)
            if work_order:
                wo_list.append(work_order)

    @frappe.whitelist()
    def make_material_request(self):
        """Create Material Requests grouped by Sales Order and Material Request Type"""
		
        material_request_list = []
        material_request_map = {}

        for item in self.mr_items:
            item_doc = frappe.get_cached_doc("Item", item.item_code)

            material_request_type = item.material_request_type or item_doc.default_material_request_type

			# key for Sales Order:Material Request Type:Customer
            key = "{}:{}:{}".format(item.sales_order, material_request_type, item_doc.customer or "")
            schedule_date = item.schedule_date or add_days(nowdate(), cint(item_doc.lead_time_days))

            if key not in material_request_map:
				# make a new MR for the combination
                material_request_map[key] = frappe.new_doc("Material Request")
                material_request = material_request_map[key]
                material_request.update(
					{
						"transaction_date": nowdate(),
						"status": "Draft",
						"company": self.company,
						"material_request_type": material_request_type,
						"customer": item_doc.customer or "",
					}
				)
                material_request_list.append(material_request)
            else:
                material_request = material_request_map[key]

			# Check for existing Draft Material Request Item to avoid duplication
            existing_mr_item = frappe.db.exists(
				"Material Request Item",
				{
					"material_request_plan_item": item.name,
					"docstatus": ["in", [0, 1]],  # Draft or Submitted
					# "docstatus": 0  # Draft
				}
			)

            if existing_mr_item:
                frappe.throw("Material Request already exists.")
                continue  # Skip this item if already exists in draft MR

			# Else, add the item to the MR
            material_request.append(
				"items",
				{
					"item_code": item.item_code,
					"from_warehouse": item.from_warehouse
					if material_request_type == "Material Transfer"
					else None,
					"qty": item.quantity,
					"schedule_date": schedule_date,
					"warehouse": item.warehouse,
					"sales_order": item.sales_order,
					"production_plan": self.name,
					"material_request_plan_item": item.name,
					"project": frappe.db.get_value("Sales Order", item.sales_order, "project")
					if item.sales_order
					else None,
					"custom_remarks": item.custom_remarks,  # Pass remarks if needed
				},
			)

        for material_request in material_request_list:
			# submit
            material_request.flags.ignore_permissions = 1
            material_request.run_method("set_missing_values")

            material_request.save()
            if self.get("submit_material_request"):
                material_request.submit()

        frappe.flags.mute_messages = False

        if material_request_list:
            material_request_list = [
                get_link_to_form("Material Request", m.name) for m in material_request_list
			]
            msgprint(_("{0} created").format(comma_and(material_request_list)))
        else:
            msgprint(_("No material request created"))







import json
from collections import defaultdict
from erpnext.manufacturing.doctype.production_plan.production_plan import get_warehouse_list
from erpnext.manufacturing.doctype.production_plan.production_plan import get_exploded_items
from erpnext.manufacturing.doctype.production_plan.production_plan import get_bin_details
from erpnext.manufacturing.doctype.production_plan.production_plan import get_material_request_items
from erpnext.manufacturing.doctype.production_plan.production_plan import get_raw_materials_of_sub_assembly_items
from erpnext.manufacturing.doctype.production_plan.production_plan import get_subitems
from erpnext.manufacturing.doctype.production_plan.production_plan import get_uom_conversion_factor
from erpnext.manufacturing.doctype.production_plan.production_plan import get_materials_from_other_locations

@frappe.whitelist()
def get_items_for_material_requests(doc, warehouses=None, get_parent_warehouse_data=None):
	if isinstance(doc, str):
		doc = frappe._dict(json.loads(doc))

	if warehouses:
		warehouses = list(set(get_warehouse_list(warehouses)))

		if (
			doc.get("for_warehouse")
			and not get_parent_warehouse_data
			and doc.get("for_warehouse") in warehouses
		):
			warehouses.remove(doc.get("for_warehouse"))

	doc["mr_items"] = []

	po_items = doc.get("po_items") if doc.get("po_items") else doc.get("items")

	if doc.get("sub_assembly_items"):
		for sa_row in doc.sub_assembly_items:
			sa_row = frappe._dict(sa_row)
			if sa_row.type_of_manufacturing == "Material Request":
				po_items.append(
					frappe._dict(
						{
							"item_code": sa_row.production_item,
							"required_qty": sa_row.qty,
							"include_exploded_items": 0,
						}
					)
				)

	# Check for empty table or empty rows
	if not po_items or not [row.get("item_code") for row in po_items if row.get("item_code")]:
		frappe.throw(
			_("Items to Manufacture are required to pull the Raw Materials associated with it."),
			title=_("Items Required"),
		)

	company = doc.get("company")
	ignore_existing_ordered_qty = doc.get("ignore_existing_ordered_qty")
	include_safety_stock = doc.get("include_safety_stock")

	so_item_details = frappe._dict()

	sub_assembly_items = defaultdict(int)
	if doc.get("skip_available_sub_assembly_item") and doc.get("sub_assembly_items"):
		for d in doc.get("sub_assembly_items"):
			sub_assembly_items[(d.get("production_item"), d.get("bom_no"))] += d.get("qty")

	for data in po_items:
		if not data.get("include_exploded_items") and doc.get("sub_assembly_items"):
			data["include_exploded_items"] = 1

		planned_qty = data.get("required_qty") or data.get("planned_qty")
		ignore_existing_ordered_qty = data.get("ignore_existing_ordered_qty") or ignore_existing_ordered_qty
		warehouse = doc.get("for_warehouse")

		item_details = {}
		if data.get("bom") or data.get("bom_no"):
			if data.get("required_qty"):
				bom_no = data.get("bom")
				include_non_stock_items = 1
				include_subcontracted_items = 1 if data.get("include_exploded_items") else 0
			else:
				bom_no = data.get("bom_no")
				include_subcontracted_items = doc.get("include_subcontracted_items")
				include_non_stock_items = doc.get("include_non_stock_items")

			if not planned_qty:
				frappe.throw(_("For row {0}: Enter Planned Qty").format(data.get("idx")))

			if bom_no:
				if data.get("include_exploded_items") and doc.get("skip_available_sub_assembly_item"):
					item_details = {}
					if doc.get("sub_assembly_items"):
						item_details = get_raw_materials_of_sub_assembly_items(
							so_item_details[doc.get("sales_order")].keys() if so_item_details else [],
							item_details,
							company,
							bom_no,
							include_non_stock_items,
							sub_assembly_items,
							planned_qty=planned_qty,
						)

				elif data.get("include_exploded_items") and include_subcontracted_items:
					# fetch exploded items from BOM
					item_details = get_exploded_items(
						item_details,
						company,
						bom_no,
						include_non_stock_items,
						planned_qty=planned_qty,
						doc=doc,
					)
				else:
					item_details = get_subitems(
						doc,
						data,
						item_details,
						bom_no,
						company,
						include_non_stock_items,
						include_subcontracted_items,
						1,
						planned_qty=planned_qty,
					)
		elif data.get("item_code"):
			item_master = frappe.get_doc("Item", data["item_code"]).as_dict()
			purchase_uom = item_master.purchase_uom or item_master.stock_uom
			conversion_factor = (
				get_uom_conversion_factor(item_master.name, purchase_uom) if item_master.purchase_uom else 1.0
			)

			item_details[item_master.name] = frappe._dict(
				{
					"item_name": item_master.item_name,
					"default_bom": doc.bom,
					"purchase_uom": purchase_uom,
					"default_warehouse": item_master.default_warehouse,
					"min_order_qty": item_master.min_order_qty,
					"default_material_request_type": item_master.default_material_request_type,
					"qty": planned_qty or 1,
					"is_sub_contracted": item_master.is_subcontracted_item,
					"item_code": item_master.name,
					"description": item_master.description,
					"stock_uom": item_master.stock_uom,
					"conversion_factor": conversion_factor,
					"safety_stock": item_master.safety_stock,
				}
			)

		sales_order = doc.get("sales_order")

		for item_code, details in item_details.items():
			so_item_details.setdefault(sales_order, frappe._dict())
			if item_code in so_item_details.get(sales_order, {}):
				so_item_details[sales_order][item_code]["qty"] = so_item_details[sales_order][item_code].get(
					"qty", 0
				) + flt(details.qty)
			else:
				so_item_details[sales_order][item_code] = details

	mr_items = []
	for sales_order in so_item_details:
		item_dict = so_item_details[sales_order]
		for details in item_dict.values():
			bin_dict = get_bin_details(details, doc.company, warehouse)
			bin_dict = bin_dict[0] if bin_dict else {}

			if details.qty > 0:
				items = get_material_request_items(
					doc,
					details,
					sales_order,
					company,
					ignore_existing_ordered_qty,
					include_safety_stock,
					warehouse,
					bin_dict,
				)
				if items:
					mr_items.append(items)

	# Initialize a defaultdict with set to store item_codes grouped by priority
	priority_materials = defaultdict(set)

	for po_item in po_items:
		bom_no = po_item.get("bom_no")
		priority = po_item.get("custom_priority")
		
		if bom_no and priority:
			# Fetch raw materials from BOM's exploded items
			exploded_items = frappe.get_all(
				"BOM Explosion Item",
				filters={"parent": bom_no},
				fields=["item_code"]
			)
			
			for item in exploded_items:
				priority_materials[priority].add(item.item_code)

	# Optional: Convert defaultdict to normal dict if needed
	priority_materials = dict(priority_materials)
				
	# Define priority levels in descending order
	priority_order = ["Urgent", "High", "Medium", "Low"]

	# Create a reverse lookup: item_code -> highest priority
	item_priority_map = {}

	for priority in priority_order:
		for item_code in priority_materials.get(priority, set()):
			# Assign only if not already assigned (higher priorities come first)
			if item_code not in item_priority_map:
				item_priority_map[item_code] = priority

	# Now apply the priority to mr_items
	for mr_item in mr_items:
		item_code = mr_item.get("item_code")
		if item_code in item_priority_map:
			mr_item["custom_priority"] = item_priority_map[item_code]

	if (not ignore_existing_ordered_qty or get_parent_warehouse_data) and warehouses:
		new_mr_items = []
		for item in mr_items:
			get_materials_from_other_locations(item, warehouses, new_mr_items, company)

		mr_items = new_mr_items

	if not mr_items:
		to_enable = frappe.bold(_("Ignore Existing Projected Quantity"))
		warehouse = frappe.bold(doc.get("for_warehouse"))
		message = (
			_(
				"As there are sufficient raw materials, Material Request is not required for Warehouse {0}."
			).format(warehouse)
			+ "<br><br>"
		)
		message += _("If you still want to proceed, please enable {0}.").format(to_enable)

		frappe.msgprint(message, title=_("Note"))

	return mr_items



	# if isinstance(doc, str):
	# 	doc = frappe._dict(json.loads(doc))

	# if warehouses:
	# 	warehouses = list(set(get_warehouse_list(warehouses)))

	# 	if (
	# 		doc.get("for_warehouse")
	# 		and not get_parent_warehouse_data
	# 		and doc.get("for_warehouse") in warehouses
	# 	):
	# 		warehouses.remove(doc.get("for_warehouse"))

	# doc["mr_items"] = []

	# po_items = doc.get("po_items") if doc.get("po_items") else doc.get("items")

	# if doc.get("sub_assembly_items"):
	# 	for sa_row in doc.sub_assembly_items:
	# 		sa_row = frappe._dict(sa_row)
	# 		if sa_row.type_of_manufacturing == "Material Request":
	# 			po_items.append(
	# 				frappe._dict(
	# 					{
	# 						"item_code": sa_row.production_item,
	# 						"required_qty": sa_row.qty,
	# 						"include_exploded_items": 0,
	# 					}
	# 				)
	# 			)

	# # Check for empty table or empty rows
	# if not po_items or not [row.get("item_code") for row in po_items if row.get("item_code")]:
	# 	frappe.throw(
	# 		_("Items to Manufacture are required to pull the Raw Materials associated with it."),
	# 		title=_("Items Required"),
	# 	)

	# company = doc.get("company")
	# ignore_existing_ordered_qty = doc.get("ignore_existing_ordered_qty")
	# include_safety_stock = doc.get("include_safety_stock")

	# so_item_details = frappe._dict()

	# sub_assembly_items = defaultdict(int)
	# if doc.get("skip_available_sub_assembly_item") and doc.get("sub_assembly_items"):
	# 	for d in doc.get("sub_assembly_items"):
	# 		sub_assembly_items[(d.get("production_item"), d.get("bom_no"))] += d.get("qty")

	# for data in po_items:
	# 	if not data.get("include_exploded_items") and doc.get("sub_assembly_items"):
	# 		data["include_exploded_items"] = 1

	# 	planned_qty = data.get("required_qty") or data.get("planned_qty")
	# 	ignore_existing_ordered_qty = data.get("ignore_existing_ordered_qty") or ignore_existing_ordered_qty
	# 	warehouse = doc.get("for_warehouse")

	# 	item_details = {}
	# 	if data.get("bom") or data.get("bom_no"):
	# 		if data.get("required_qty"):
	# 			bom_no = data.get("bom")
	# 			include_non_stock_items = 1
	# 			include_subcontracted_items = 1 if data.get("include_exploded_items") else 0
	# 		else:
	# 			bom_no = data.get("bom_no")
	# 			include_subcontracted_items = doc.get("include_subcontracted_items")
	# 			include_non_stock_items = doc.get("include_non_stock_items")

	# 		if not planned_qty:
	# 			frappe.throw(_("For row {0}: Enter Planned Qty").format(data.get("idx")))

	# 		if bom_no:
	# 			if data.get("include_exploded_items") and doc.get("skip_available_sub_assembly_item"):
	# 				item_details = {}
	# 				if doc.get("sub_assembly_items"):
	# 					item_details = get_raw_materials_of_sub_assembly_items(
	# 						so_item_details[doc.get("sales_order")].keys() if so_item_details else [],
	# 						item_details,
	# 						company,
	# 						bom_no,
	# 						include_non_stock_items,
	# 						sub_assembly_items,
	# 						planned_qty=planned_qty,
	# 					)

	# 			elif data.get("include_exploded_items") and include_subcontracted_items:
	# 				# fetch exploded items from BOM
	# 				item_details = get_exploded_items(
	# 					item_details,
	# 					company,
	# 					bom_no,
	# 					include_non_stock_items,
	# 					planned_qty=planned_qty,
	# 					doc=doc,
	# 				)
	# 			else:
	# 				item_details = get_subitems(
	# 					doc,
	# 					data,
	# 					item_details,
	# 					bom_no,
	# 					company,
	# 					include_non_stock_items,
	# 					include_subcontracted_items,
	# 					1,
	# 					planned_qty=planned_qty,
	# 				)
	# 	elif data.get("item_code"):
	# 		item_master = frappe.get_doc("Item", data["item_code"]).as_dict()
	# 		purchase_uom = item_master.purchase_uom or item_master.stock_uom
	# 		conversion_factor = (
	# 			get_uom_conversion_factor(item_master.name, purchase_uom) if item_master.purchase_uom else 1.0
	# 		)

	# 		item_details[item_master.name] = frappe._dict(
	# 			{
	# 				"item_name": item_master.item_name,
	# 				"default_bom": doc.bom,
	# 				"purchase_uom": purchase_uom,
	# 				"default_warehouse": item_master.default_warehouse,
	# 				"min_order_qty": item_master.min_order_qty,
	# 				"default_material_request_type": item_master.default_material_request_type,
	# 				"qty": planned_qty or 1,
	# 				"is_sub_contracted": item_master.is_subcontracted_item,
	# 				"item_code": item_master.name,
	# 				"description": item_master.description,
	# 				"stock_uom": item_master.stock_uom,
	# 				"conversion_factor": conversion_factor,
	# 				"safety_stock": item_master.safety_stock,
	# 			}
	# 		)

	# 	sales_order = doc.get("sales_order")

	# 	for item_code, details in item_details.items():
	# 		so_item_details.setdefault(sales_order, frappe._dict())
	# 		if item_code in so_item_details.get(sales_order, {}):
	# 			so_item_details[sales_order][item_code]["qty"] = so_item_details[sales_order][item_code].get(
	# 				"qty", 0
	# 			) + flt(details.qty)
	# 		else:
	# 			so_item_details[sales_order][item_code] = details

	# # Priority order map
	# priority_rank = {
	# 	"Urgent": 1,
	# 	"High": 2,
	# 	"Medium": 3,
	# 	"Low": 4
	# }

	# # Build BOM to Priority mapping once
	# bom_to_priority = {}

	# # Direct BOM priorities
	# for row in doc.get("po_items", []):
	# 	if row.get("bom_no"):
	# 		bom_to_priority[row["bom_no"]] = {
	# 			"priority": row.get("custom_priority")
	# 		}

	# # Sub-Assembly BOMs inherit from parent item
	# for row_sa in doc.get("sub_assembly_items", []):
	# 	if row_sa.get("bom_no"):
	# 		for row in doc.get("po_items", []):
	# 			if row.get("bom_no") and row["item_code"] == row_sa["parent_item_code"]:
	# 				existing_priority = bom_to_priority.get(row_sa["bom_no"], {}).get("priority")
	# 				new_priority = row.get("custom_priority")

	# 				if not existing_priority or (
	# 					priority_rank.get(new_priority, 999) < priority_rank.get(existing_priority, 999)
	# 				):
	# 					bom_to_priority[row_sa["bom_no"]] = {
	# 						"priority": new_priority
	# 					}

	# for item_code, detail in item_details.items():
	# 	so_item_details.setdefault(sales_order, frappe._dict())

	# 	# Find the BOM that this raw material came from
	# 	source_bom = data.get("bom") or data.get("bom_no")

	# 	# Inject custom_priority based on BOM
	# 	if source_bom and source_bom in bom_to_priority:
	# 		detail["custom_priority"] = bom_to_priority[source_bom]["priority"]

	# 	# if item_code in so_item_details.get(sales_order, {}):
	# 	# 	so_item_details[sales_order][item_code]["qty"] += flt(detail.qty)
	# 	# else:
	# 	# 	so_item_details[sales_order][item_code] = detail

	# # Now generate Material Request items
	# mr_items = []
	# for sales_order in so_item_details:
	# 	item_dict = so_item_details[sales_order]
	# 	for details in item_dict.values():
	# 		bin_dict = get_bin_details(details, doc.company, warehouse)
	# 		bin_dict = bin_dict[0] if bin_dict else {}

	# 		if details.qty > 0:
	# 			items = get_material_request_items(
	# 				doc,
	# 				details,
	# 				sales_order,
	# 				company,
	# 				ignore_existing_ordered_qty,
	# 				include_safety_stock,
	# 				warehouse,
	# 				bin_dict,
	# 			)
	# 			if items:
	# 				for item_detail in item_details.values():
	# 					if item_detail.get("item_code") == items.get("item_code"):
	# 						items["custom_priority"] = item_detail.get("custom_priority")
	# 				mr_items.append(items)
	# 				print(item_details.values())

	# if (not ignore_existing_ordered_qty or get_parent_warehouse_data) and warehouses:
	# 	new_mr_items = []
	# 	for item in mr_items:
	# 		get_materials_from_other_locations(item, warehouses, new_mr_items, company)

	# 	mr_items = new_mr_items

	# if not mr_items:
	# 	to_enable = frappe.bold(_("Ignore Existing Projected Quantity"))
	# 	warehouse = frappe.bold(doc.get("for_warehouse"))
	# 	message = (
	# 		_(
	# 			"As there are sufficient raw materials, Material Request is not required for Warehouse {0}."
	# 		).format(warehouse)
	# 		+ "<br><br>"
	# 	)
	# 	message += _("If you still want to proceed, please enable {0}.").format(to_enable)

	# 	frappe.msgprint(message, title=_("Note"))

	# return mr_items
