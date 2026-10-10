
from datetime import datetime, timedelta
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



def _get_doctor_name(doctor):
    """Accept either a Doctor Profile name or the doctor's User ID."""
    if not doctor:
        frappe.throw(_("Doctor is required"))

    if frappe.db.exists("Doctor Profile", doctor):
        return doctor

    doctor_name = frappe.db.get_value(
        "Doctor Profile",
        {"user": doctor},
        "name",
    )

    if not doctor_name:
        frappe.throw(_("Doctor does not exist"))

    return doctor_name


def _get_hospital_settings():
    settings = frappe.get_single("Hospital Settings")

    if not settings.opening_time or not settings.closing_time:
        frappe.throw(_("Set hospital opening and closing times first"))

    duration = int(settings.appointment_duration or 30)
    buffer_minutes = int(settings.buffer_minutes or 0)

    if duration <= 0 or buffer_minutes < 0:
        frappe.throw(_("Invalid appointment duration or buffer"))

    return settings, duration, buffer_minutes


def _is_hospital_holiday(date):
    """Check weekly holidays and hospital-wide holiday dates."""
    settings = frappe.get_single("Hospital Settings")
    weekday = frappe.utils.getdate(date).strftime("%A")

    weekly_holidays = [
        row.day for row in settings.weekly_holidays
    ]

    if weekday in weekly_holidays:
        return True

    holidays = frappe.get_all(
        "Hospital Holiday",
        filters={
            "start_date": ["<=", date],
            "end_date": [">=", date],
            "applies_to_all_doctors": 1,
        },
        pluck="name",
    )

    return bool(holidays)


def _doctor_has_leave(doctor_name, date, start_time, end_time):
    """Return True when a slot overlaps approved doctor leave."""
    exceptions = frappe.get_all(
        "Doctor Availability Exception",
        filters={
            "doctor": doctor_name,
            "approved": 1,
            "start_date": ["<=", date],
            "end_date": [">=", date],
        },
        fields=[
            "exception_type",
            "start_time",
            "end_time",
        ],
    )

    for exception in exceptions:
        if exception.exception_type == "Full Day Leave":
            return True

        if exception.exception_type == "Partial Day Leave":
            if not exception.start_time or not exception.end_time:
                # Incomplete partial-day leave should fail closed.
                return True

            leave_start = frappe.utils.get_time(exception.start_time)
            leave_end = frappe.utils.get_time(exception.end_time)
            slot_start = frappe.utils.get_time(start_time)
            slot_end = frappe.utils.get_time(end_time)

            # Overlapping time ranges are unavailable.
            if slot_start < leave_end and slot_end > leave_start:
                return True

    return False


def _slot_is_booked(doctor_name, date, start_time, end_time):
    """Check stored slots and active appointments for conflicts."""
    existing_slots = frappe.get_all(
        "Availability Slot",
        filters={
            "doctor": doctor_name,
            "date": date,
            "is_booked": 1,
        },
        fields=["start_time", "end_time"],
    )

    slot_start = frappe.utils.get_time(start_time)
    slot_end = frappe.utils.get_time(end_time)

    for existing in existing_slots:
        existing_start = frappe.utils.get_time(existing.start_time)
        existing_end = frappe.utils.get_time(existing.end_time)

        if slot_start < existing_end and slot_end > existing_start:
            return True

    active_appointments = frappe.get_all(
        "Appointment",
        filters={
            "doctor": doctor_name,
            "appointment_date": date,
            "status": ["not in", ["Cancelled"]],
            "docstatus": ["!=", 2],
        },
        fields=["appointment_time"],
    )

    settings = frappe.get_single("Hospital Settings")
    duration = int(settings.appointment_duration or 30)
    buffer_minutes = int(settings.buffer_minutes or 0)

    for appointment in active_appointments:
        appointment_start = frappe.utils.get_time(
            appointment.appointment_time
        )
        appointment_end = (
            datetime.combine(
                frappe.utils.getdate(date),
                appointment_start,
            )
            + timedelta(minutes=duration + buffer_minutes)
        ).time()

        if slot_start < appointment_end and slot_end > appointment_start:
            return True

    return False


@frappe.whitelist()
def get_available_slots(doctor, date):
    """Generate available appointment slots for one doctor and date."""
    doctor_name = _get_doctor_name(doctor)
    date = frappe.utils.getdate(date)
    today = frappe.utils.getdate()

    if date < today:
        return []

    settings, duration, buffer_minutes = _get_hospital_settings()

    booking_window = int(settings.booking_window_days or 30)
    if date > today + timedelta(days=booking_window):
        return []

    if not frappe.db.get_value(
        "Doctor Profile", doctor_name, "is_approved"
    ):
        return []

    if _is_hospital_holiday(date):
        return []

    opening = frappe.utils.get_time(settings.opening_time)
    closing = frappe.utils.get_time(settings.closing_time)

    opening_dt = datetime.combine(date, opening)
    closing_dt = datetime.combine(date, closing)

    if closing_dt <= opening_dt:
        frappe.throw(_("Hospital closing time must be after opening time"))

    minimum_notice = int(settings.minimum_booking_notice or 0)
    earliest_allowed = frappe.utils.now_datetime() + timedelta(
        minutes=minimum_notice
    )

    slots = []
    current = opening_dt

    while current + timedelta(minutes=duration) <= closing_dt:
        slot_start = current
        slot_end = current + timedelta(minutes=duration)

        start_time = slot_start.time()
        end_time = slot_end.time()

        if slot_start >= earliest_allowed:
            if not _doctor_has_leave(
                doctor_name, date, start_time, end_time
            ):
                if not _slot_is_booked(
                    doctor_name, date, start_time, end_time
                ):
                    slots.append({
                        "start_time": start_time.strftime("%H:%M:%S"),
                        "end_time": end_time.strftime("%H:%M:%S"),
                        "time": start_time.strftime("%H:%M:%S"),
                    })

        current += timedelta(minutes=duration + buffer_minutes)

    return slots