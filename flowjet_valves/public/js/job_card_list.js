frappe.listview_settings["Job Card"] = {
    onload: function (listview) {
        frappe.call({
            method: "flowjet_valves.public.py.work_order.get_excluded_work_orders",
            callback: function (r) {
				if (r.message && Array.isArray(r.message) && r.message.length > 0) {
					// // Clear all existing filters
					// listview.filter_area.clear();
					// Apply filter: work_order not in r.message
					listview.filter_area.add([
						["Job Card", "work_order", "not in", r.message]
					]);
				}
            },
        });
    },
	has_indicator_for_draft: true,
	add_fields: ["expected_start_date", "expected_end_date"],
	get_indicator: function (doc) {
		const status_colors = {
			"Work In Progress": "orange",
			Completed: "green",
			Cancelled: "red",
			"Material Transferred": "blue",
			Open: "red",
		};
		const status = doc.status || "Open";
		const color = status_colors[status] || "blue";

		return [__(status), color, `status,=,${status}`];
	},
};
