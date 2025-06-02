app_name = "flowjet_valves"
app_title = "Flowjet Valves"
app_publisher = "Sanskar Technolab pvt ltd"
app_description = "Main Customizations"
app_email = "meet@sanskartechnolab.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "flowjet_valves",
# 		"logo": "/assets/flowjet_valves/logo.png",
# 		"title": "Flowjet Valves",
# 		"route": "/flowjet_valves",
# 		"has_permission": "flowjet_valves.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/flowjet_valves/css/flowjet_valves.css"
# app_include_js = "/assets/flowjet_valves/js/flowjet_valves.js"

# include js, css files in header of web template
# web_include_css = "/assets/flowjet_valves/css/flowjet_valves.css"
# web_include_js = "/assets/flowjet_valves/js/flowjet_valves.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "flowjet_valves/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Sales Order" : "public/js/sales_order.js",
    "Production Plan" : "public/js/production_plan.js",
    "Work Order" : "public/js/work_order.js",
    "Purchase Order" : "public/js/purchase_order.js",
    "Job Card" : "public/js/job_card.js",
    "Opportunity" : "public/js/opportunity.js",
    "Quotation" : "public/js/quotation.js",
    "Item" : "public/js/item.js",
    "Material Request" : "public/js/material_request.js",
    "Purchase Receipt" : "public/js/purchase_receipt.js",
}
doctype_list_js = {
    "Work Order" : "public/js/work_order_list.js",
    "Job Card" : "public/js/job_card_list.js",
}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "flowjet_valves/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "flowjet_valves.utils.jinja_methods",
# 	"filters": "flowjet_valves.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "flowjet_valves.install.before_install"
# after_install = "flowjet_valves.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "flowjet_valves.uninstall.before_uninstall"
# after_uninstall = "flowjet_valves.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "flowjet_valves.utils.before_app_install"
# after_app_install = "flowjet_valves.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "flowjet_valves.utils.before_app_uninstall"
# after_app_uninstall = "flowjet_valves.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "flowjet_valves.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
    "Production Plan": "flowjet_valves.public.py.production_plan.CustomProductionPlan",
    "Work Order": "flowjet_valves.public.py.work_order.CustomWorkOrder",
    "Job Card": "flowjet_valves.public.py.job_card.CustomJobCard"
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Material Request": {
        "before_insert": "flowjet_valves.public.py.material_request.copy_custom_fields"
    },
    "Job Card": {
        "before_save": "flowjet_valves.public.py.job_card.update_totals",
        "before_submit": "flowjet_valves.public.py.job_card.update_totals",
        # "on_update": "flowjet_valves.public.py.job_card.update_pending_qty",
        # "after_save": "flowjet_valves.public.py.job_card.update_pending_qty",
    },
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"flowjet_valves.tasks.all"
# 	],
# 	"daily": [
# 		"flowjet_valves.tasks.daily"
# 	],
# 	"hourly": [
# 		"flowjet_valves.tasks.hourly"
# 	],
# 	"weekly": [
# 		"flowjet_valves.tasks.weekly"
# 	],
# 	"monthly": [
# 		"flowjet_valves.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "flowjet_valves.install.before_tests"

# Overriding Methods
# ------------------------------

override_whitelisted_methods = {
    # "erpnext.manufacturing.doctype.production_plan.production_plan.get_sales_orders": "flowjet_valves.public.py.production_plan.custom_get_sales_orders",
    "erpnext.manufacturing.doctype.production_plan.production_plan.get_items_for_material_requests": "flowjet_valves.public.py.production_plan.get_items_for_material_requests",
    "erpnext.manufacturing.doctype.production_plan.production_plan.make_material_request": "flowjet_valves.public.py.production_plan.make_material_request"
}

#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "flowjet_valves.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["flowjet_valves.utils.before_request"]
# after_request = ["flowjet_valves.utils.after_request"]

# Job Events
# ----------
# before_job = ["flowjet_valves.utils.before_job"]
# after_job = ["flowjet_valves.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"flowjet_valves.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

fixtures = [
    "Workflow",
]