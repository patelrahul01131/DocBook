
from os import error
import frappe

@frappe.whitelist(allow_guest=True)
def list_appointment(patient):
    
    selected_patient = patient
    
    filters = {
        "patient": selected_patient,
    }
    
    appointments = frappe.get_all(
        "Appointment",
        filters=filters,
        fields=[
            "patient",
            "doctor",
            "slot",
            "appointment_date",
            "appointment_time",
            "status",
            "reason",
            "consultation_fee",
            "payment_status",
            "created_at",
        ],
    )
    
    return appointments



@frappe.whitelist(allow_guest=True)
def show_appointment(appointment_id):
    # appointment = frappe.get_doc("Appointment", appointment_id)

    appointment = frappe.db.sql("""
        SELECT * FROM `tabAppointment` WHERE slot = %s
    """, appointment_id, as_dict=True)

    return appointment



import frappe
from frappe import _


@frappe.whitelist(allow_guest=True)
def create_appointment(
    patient,
    doctor,
    appointment_date,
    appointment_time,
    reason=None
):
    try:

        # -----------------------------
        # Validate required fields
        # -----------------------------

        if not patient:
            frappe.throw(_("Patient is required"))

        if not doctor:
            frappe.throw(_("Doctor is required"))

        if not appointment_date:
            frappe.throw(_("Appointment date is required"))

        if not appointment_time:
            frappe.throw(_("Appointment time is required"))


        # -----------------------------
        # Check patient
        # -----------------------------

        if not frappe.db.exists("Patient Profile", patient):
            frappe.throw(_("Patient does not exist"))


        # -----------------------------
        # Get doctor
        # -----------------------------

        doctor_name = frappe.db.exists(
            "Doctor Profile",
            {
                "user": doctor
            }
        )

        if not doctor_name:
            frappe.throw(_("Doctor does not exist"))


        doctor_data = frappe.db.get_value(
            "Doctor Profile",
            doctor_name,
            [
                "user",
                "is_approved",
                "consultation_fee"
            ],
            as_dict=True
        )

        if not doctor_data:
            frappe.throw(
                _("Doctor information could not be found")
            )


        if not doctor_data.is_approved:
            frappe.throw(
                _("This doctor is not approved for appointments")
            )


        # -----------------------------
        # Validate date
        # -----------------------------

        appointment_date = frappe.utils.getdate(
            appointment_date
        )

        today = frappe.utils.getdate()

        if appointment_date < today:
            frappe.throw(
                _("You cannot book an appointment for a past date")
            )


        # -----------------------------
        # Validate time
        # -----------------------------

        appointment_time = frappe.utils.get_time(
            appointment_time
        )


        # -----------------------------
        # Check duplicate appointment
        # -----------------------------

        existing_appointment = frappe.db.exists(
            "Appointment",
            {
                "doctor": doctor_name,
                "appointment_date": appointment_date,
                "appointment_time": appointment_time,
                "docstatus": ["!=", 2],
                "status": [
                    "not in",
                    ["Cancelled", "Rejected"]
                ]
            }
        )

        if existing_appointment:
            frappe.throw(
                _("Doctor already has an appointment at this time")
            )


        # -----------------------------
        # CREATE SLOT
        # -----------------------------

        from datetime import datetime, timedelta

        # -----------------------------
# CREATE AVAILABILITY SLOT
# -----------------------------

        duration = (
            frappe.db.get_single_value(
                "Hospital Settings",
                "appointment_duration"
            ) or 30
        )

        start_datetime = datetime.combine(
            appointment_date,
            appointment_time
        )

        end_time = (
            start_datetime + timedelta(minutes=duration)
        ).time()

        
        slot = frappe.get_doc({
            "doctype": "Availability Slot",
            "doctor": doctor_name,
            "date": appointment_date,
            "start_time": appointment_time,
            "end_time": end_time,
            "is_booked": 1
        })

        # slot.insert()
        slot.insert(ignore_permissions=True)


        # -----------------------------
        # CREATE APPOINTMENT
        # -----------------------------

        appointment = frappe.get_doc({
            "doctype": "Appointment",

            "patient": patient,

            "doctor": doctor,

            "slot": slot.name,

            "appointment_date": appointment_date,

            "appointment_time": appointment_time,

            "status": "Pending",

            "reason": reason or "",

            "consultation_fee":
                doctor_data.consultation_fee or 0,

            "payment_status": "Pending"
        })

        appointment.insert(ignore_permissions=True)

        frappe.db.commit()


        return {
            "success": True,

            "message":
                _("Appointment booked successfully"),

            "appointment":
                appointment.name,

            "slot":
                slot.name
        }


    except frappe.exceptions.ValidationError:

        frappe.db.rollback()

        raise


    except Exception:

        frappe.db.rollback()

        frappe.log_error(
            frappe.get_traceback(),
            "Create Appointment Error"
        )

        frappe.throw(
            _("Unable to create appointment. Please try again.")
        )
