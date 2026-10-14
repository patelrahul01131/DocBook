"""
Shared authorization helpers for DocBook APIs.
"""

import frappe
from frappe import _


def require_login():
	if frappe.session.user == "Guest" or not frappe.session.user:
		frappe.throw(_("Please log in first"), frappe.AuthenticationError)


def is_admin():
	return "System Manager" in frappe.get_roles(frappe.session.user)


def has_role(*roles):
	user_roles = frappe.get_roles(frappe.session.user)
	return any(r in user_roles for r in roles)


def is_receptionist():
	return has_role("Receptionist")


def is_laboratory():
	return has_role("Laboratory")


def current_doctor(user=None):
	user = user or frappe.session.user
	if not user or user == "Guest":
		return None
	return frappe.db.get_value("Doctor Profile", {"user": user}, "name")


def current_patient(user=None):
	"""Resolve the Patient Profile name for the session (or given user), or None."""
	user = user or frappe.session.user
	if not user or user == "Guest":
		return None
	if frappe.db.exists("Patient Profile", user):
		return user
	return frappe.db.get_value("Patient Profile", {"user": user}, "name")


def can_manage_reports():
	"""Lab, receptionist, doctors, and admins can manage reports."""
	return is_admin() or is_laboratory() or is_receptionist() or bool(current_doctor())
