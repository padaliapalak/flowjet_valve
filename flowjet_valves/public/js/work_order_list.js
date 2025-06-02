frappe.listview_settings["Work Order"] = {
    onload: function (listview) {
        frappe.call({
            method: "flowjet_valves.public.py.work_order.get_excluded_work_orders",
            callback: function (r) {
				if (r.message && Array.isArray(r.message) && r.message.length > 0) {
					// // Clear all existing filters
					// listview.filter_area.clear();
					// Apply filter: name not in r.message
					listview.filter_area.add([
						["Work Order", "name", "not in", r.message]
					]);
				}
            },
        });
    },
    add_fields: [
        "bom_no",
        "status",
        "sales_order",
        "qty",
        "produced_qty",
        "expected_delivery_date",
        "planned_start_date",
        "planned_end_date",
    ],
    filters: [["status", "!=", "Stopped"]],
    get_indicator: function (doc) {
        if (doc.status === "Submitted") {
            return [__("Not Started"), "orange", "status,=,Submitted"];
        } else {
            return [
                __(doc.status),
                {
                    Draft: "red",
                    Stopped: "red",
                    "Not Started": "red",
                    "In Process": "orange",
                    Completed: "green",
                    Cancelled: "gray",
                }[doc.status],
                "status,=," + doc.status,
            ];
        }
    },
};
