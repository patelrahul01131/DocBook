
import frappe
from frappe import _



import frappe
from frappe import _


@frappe.whitelist(allow_guest=True)
def signup(full_name, email, password, phone=None):
    """Public signup for patients only."""

    full_name = (full_name or "").strip()
    email = (email or "").strip().lower()

    if not full_name or not email or not password:
        frappe.throw(_("Name, email and password are required"))

    if len(password) < 8:
        frappe.throw(_("Password must contain at least 8 characters"))

    if frappe.db.exists("User", email):
        frappe.throw(_("An account with this email already exists"))

    # Create the user with the Patient role by default.
    user = frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": full_name,
        "enabled": 1,
        "user_type": "Website User",
        "send_welcome_email": 0,
        "roles": [
            {
                "role": "Patient"
            }
        ]
    })

    user.insert(ignore_permissions=True)

    # Set the password.
    user.new_password = password
    user.save(ignore_permissions=True)

    # Create the Patient Profile.
    patient = frappe.get_doc({
        "doctype": "Patient Profile",
        "user": email,
        "full_name": full_name,
        "phone": phone or ""
    })

    patient.insert(ignore_permissions=True)

    return {
        "success": True,
        "message": "Patient account created successfully"
    }

import frappe
from frappe import _


@frappe.whitelist()
def get_current_user():
    email = frappe.session.user

    if email == "Guest":
        frappe.throw(_("Please log in first"))

    user_data = frappe.db.get_value(
        "User",
        email,
        ["email", "full_name", "user_image"],
        as_dict=True
    )

    if not user_data:
        frappe.throw(_("User account not found"))

    doctor = frappe.db.exists(
        "Doctor Profile",
        {"user": email}
    )

    if doctor:
        role = "Doctor"
        redirect = "/doctor"
    else:
        patient = frappe.db.exists(
            "Patient Profile",
            {"user": email}
        )

        if patient:
            role = "Patient"
            redirect = "/find-doctors"
        else:
            frappe.throw(
                _("No DocBook profile is linked to this account")
            )

    return {
        "email": user_data.email,
        "full_name": user_data.full_name,
        "user_image": user_data.user_image,
        "role": role,
        "redirect": redirect
    }


@frappe.whitelist()
def logout_user():
    frappe.local.login_manager.logout()
    return {"success": True}
    """Identify the logged-in DocBook user."""

    email = frappe.session.user

    if email == "Guest":
        frappe.throw(_("Please log in first"))

    # Doctor accounts must already have a doctor profile.
    doctor = frappe.db.exists(
        "Doctor Profile",
        {"user": email}
    )

    if doctor:
        return {
            "role": "Doctor",
            "redirect": "/doctor"
        }

    patient = frappe.db.exists(
        "Patient Profile",
        {"user": email}
    )

    if patient:
        return {
            "role": "Patient",
            "redirect": "/home"
        }

    frappe.throw(_("No DocBook profile is linked to this account"))