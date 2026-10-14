"""
Idempotent creation of DocBook custom roles.
Wired via after_migrate in hooks.py so roles always exist after deploy.
"""

import frappe


ROLES = (
	"Receptionist",
	"Laboratory",
)


def create_custom_roles():
	"""Create the custom DocBook roles if they do not already exist."""
	for role_name in ROLES:
		if not frappe.db.exists("Role", role_name):
			role = frappe.get_doc({
				"doctype": "Role",
				"role_name": role_name,
				"desk_access": 1,
			})
			role.insert(ignore_permissions=True)
	frappe.db.commit()
