"""
Medicine catalog API — read-only browsing endpoints.
Only active medicines are exposed to non-admin users.
"""

import frappe
from frappe import _


def _require_auth():
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in first"), frappe.AuthenticationError)


# ---------------------------------------------------------------------------
# Public / authenticated listing
# ---------------------------------------------------------------------------

@frappe.whitelist()
def list_medicines(search=None, category=None, page=1, page_size=20):
	"""Return active medicines for the catalog browser."""
	_require_auth()

	filters = {"is_active": 1}

	if category:
		filters["medicine_category"] = category

	conditions = []
	values = {"is_active": 1}

	base_filter_sql = " AND is_active = 1"

	if category:
		base_filter_sql += " AND medicine_category = %(category)s"
		values["category"] = category

	if search:
		search_sql = """ AND (
			medicine_name LIKE %(search)s
			OR generic_name LIKE %(search)s
			OR brand_name LIKE %(search)s
		)"""
		base_filter_sql += search_sql
		values["search"] = f"%{search}%"

	try:
		page = max(1, int(page))
		page_size = min(100, max(1, int(page_size)))
	except (ValueError, TypeError):
		page, page_size = 1, 20

	offset = (page - 1) * page_size
	values["limit"] = page_size
	values["offset"] = offset

	medicines = frappe.db.sql(
		f"""
		SELECT
			name,
			medicine_name,
			generic_name,
			brand_name,
			medicine_category,
			strength,
			dosage_form,
			uses,
			medicine_image,
			is_active
		FROM `tabMedicine`
		WHERE 1=1 {base_filter_sql}
		ORDER BY medicine_name ASC
		LIMIT %(limit)s OFFSET %(offset)s
		""",
		values,
		as_dict=True,
	)

	return medicines


@frappe.whitelist()
def get_medicine_detail(medicine_name):
	"""Return full details for a single active medicine."""
	_require_auth()

	if not medicine_name:
		frappe.throw(_("Medicine name is required"))

	doc = frappe.db.get_value(
		"Medicine",
		medicine_name,
		[
			"name",
			"medicine_name",
			"generic_name",
			"brand_name",
			"medicine_category",
			"strength",
			"dosage_form",
			"description",
			"uses",
			"how_it_works",
			"common_side_effects",
			"precautions",
			"storage_instructions",
			"information_source",
			"is_active",
			"medicine_image",
		],
		as_dict=True,
	)

	if not doc:
		frappe.throw(_("Medicine not found"), frappe.DoesNotExistError)

	is_admin = "System Manager" in frappe.get_roles(frappe.session.user)
	if not doc.is_active and not is_admin:
		frappe.throw(_("Medicine not found"), frappe.DoesNotExistError)

	return doc


@frappe.whitelist()
def get_medicine_categories():
	"""Return the available medicine categories."""
	_require_auth()

	meta = frappe.get_meta("Medicine")
	category_field = meta.get_field("medicine_category")
	if category_field and category_field.options:
		return [c for c in category_field.options.split("\n") if c.strip()]
	return []


@frappe.whitelist()
def search_medicines(query, limit=10):
	"""Quick search for medicine name suggestions (for doctor prescription form)."""
	_require_auth()

	if not query:
		return []

	medicines = frappe.db.sql(
		"""
		SELECT name, medicine_name, generic_name, brand_name, strength, dosage_form
		FROM `tabMedicine`
		WHERE is_active = 1
		  AND (
			  medicine_name LIKE %(q)s
			  OR generic_name LIKE %(q)s
			  OR brand_name LIKE %(q)s
		  )
		ORDER BY medicine_name ASC
		LIMIT %(limit)s
		""",
		{"q": f"%{query}%", "limit": int(limit)},
		as_dict=True,
	)

	return medicines
