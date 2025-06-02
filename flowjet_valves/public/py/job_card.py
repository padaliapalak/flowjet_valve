# import frappe

# def update_pending_qty(doc, event):
#     if doc.total_completed_qty == 0:
#         frappe.db.sql("""
#             UPDATE `tabJob Card`
#             SET process_loss_qty = for_quantity - total_completed_qty
#             WHERE docstatus < 2
#         """, ())
#         frappe.db.commit()

#     frappe.msgprint(str(doc.for_quantity))
#     frappe.msgprint(str(doc.total_completed_qty))
#     frappe.msgprint(str(doc.process_loss_qty))
#     # doc.save()

import frappe
from frappe.utils import flt
from erpnext.manufacturing.doctype.job_card.job_card import JobCard
from frappe import _, bold

def update_totals(doc, method):
    """Update total_completed_qty and process_loss_qty with PO-based values"""

    # Sum completed_qty from time_logs
    time_log_completed = sum(flt(row.completed_qty or 0) for row in doc.get("time_logs") or [])

    # Sum received_qty from child table `custom_subcontract_details`
    received_qty = sum(flt(row.received_qty or 0) for row in doc.get("custom_subcontract_details") or [])

    total_completed = flt(time_log_completed) + flt(received_qty)
    doc.total_completed_qty = total_completed
    doc.custom_total_completed_inhouse_qty = flt(time_log_completed)

    # Calculate process loss
    doc.process_loss_qty = flt(doc.for_quantity or 0) - total_completed



class CustomJobCard(JobCard):
    def validate_job_card(self):
        if self.work_order and frappe.get_cached_value("Work Order", self.work_order, "status") == "Stopped":
            frappe.throw(
                _("Transaction not allowed against stopped Work Order {0}").format(
                    frappe.utils.get_link_to_form("Work Order", self.work_order)
                )
            )

        # 🔁 CHANGED CONDITION
        if not self.time_logs and self.for_quantity != self.total_completed_qty:
            frappe.throw(
                _("Time logs are required for {0} {1}").format(
                    bold("Job Card"), frappe.utils.get_link_to_form("Job Card", self.name)
                )
            )
        else:
            for row in self.time_logs:
                if not row.from_time or not row.to_time:
                    frappe.throw(_("Row #{0}: From Time and To Time fields are required").format(row.idx))

        precision = self.precision("total_completed_qty")
        total_completed_qty = flt(self.total_completed_qty, precision) + flt(self.process_loss_qty, precision)

        if self.for_quantity and flt(total_completed_qty, precision) != flt(self.for_quantity, precision):
            frappe.throw(
                _("The {0} ({1}) must be equal to {2} ({3})").format(
                    bold(_("Total Completed Qty")),
                    bold(flt(total_completed_qty, precision)),
                    bold(_("Qty to Manufacture")),
                    bold(self.for_quantity),
                )
            )
