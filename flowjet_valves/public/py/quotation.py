import frappe
from frappe import _

@frappe.whitelist()
def get_last_item_rate(party_name, item_code):
    if not (party_name and item_code):
        return None

    quotation_names = frappe.get_all("Quotation", filters={
        "party_name": party_name,
        "docstatus": 1
    }, fields=["name"], order_by="transaction_date desc", limit=5)

    if not quotation_names:
        return None

    names = [q.name for q in quotation_names]

    item = frappe.get_all("Quotation Item", filters={
        "parent": ["in", names],
        "item_code": item_code
    }, fields=["base_rate"], order_by="creation desc", limit=1)

    return item[0]["base_rate"] if item else None
