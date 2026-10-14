
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



import frappe


@frappe.whitelist(allow_guest=True)
def get_current_user():
    current_user = frappe.session.user

    # A guest is a valid state, not an authentication error.
    if not current_user or current_user == "Guest":
        return {
            "logged_in": False,
            "is_guest": True,
            "user": None,
            "email": None,
            "full_name": None,
            "role": None,
        }

    user_data = frappe.db.get_value(
        "User",
        current_user,
        ["email", "full_name", "user_image"],
        as_dict=True,
    )

    if not user_data:
        return {
            "logged_in": False,
            "is_guest": True,
            "user": None,
            "email": None,
            "full_name": None,
            "role": None,
        }

    # Identify the user's DocBook profile from the database.
    doctor = frappe.db.get_value(
        "Doctor Profile",
        {"user": current_user},
        ["name", "full_name", "phone"],
        as_dict=True,
    )

    if doctor:
        role = "Doctor"
        profile_name = doctor.name
        full_name = doctor.full_name or user_data.full_name
        phone = doctor.phone
    else:
        patient = frappe.db.get_value(
            "Patient Profile",
            {"user": current_user},
            ["name", "full_name", "phone"],
            as_dict=True,
        )

        if patient:
            role = "Patient"
            profile_name = patient.name
            full_name = patient.full_name or user_data.full_name
            phone = patient.phone
        else:
            # Staff accounts (Receptionist / Laboratory) without a DocBook
            # patient/doctor profile.
            user_roles = frappe.get_roles(current_user)
            if "Receptionist" in user_roles:
                role = "Receptionist"
            elif "Laboratory" in user_roles:
                role = "Laboratory"
            else:
                role = "User"
            profile_name = None
            full_name = user_data.full_name
            phone = None

    return {
        "logged_in": True,
        "is_guest": False,
        "user": current_user,
        "email": user_data.email,
        "full_name": full_name,
        "user_image": user_data.user_image,
        "role": role,
        "profile_name": profile_name,
        "phone": phone,
    }


    

@frappe.whitelist()
def logout_user():
    frappe.local.login_manager.logout()
    return {"success": True}


@frappe.whitelist()
def get_login_redirect():
    """Identify the logged-in DocBook user and their portal redirect."""
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

    # Staff portal roles.
    roles = frappe.get_roles(email)
    if "Receptionist" in roles:
        return {"role": "Receptionist", "redirect": "/receptionist"}
    if "Laboratory" in roles:
        return {"role": "Laboratory", "redirect": "/laboratory"}

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