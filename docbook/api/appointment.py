"""
DocBook Appointment API
Production-grade validations, scheduling, slot management, and full lifecycle operations.
"""

from datetime import datetime, date, time, timedelta
import frappe
from frappe import _


# ---------------------------------------------------------------------------
# Helpers & Resolvers
# ---------------------------------------------------------------------------

def _get_hospital_settings():
    """Retrieve and ensure Hospital Settings with production-grade defaults."""
    settings = frappe.get_single("Hospital Settings")

    opening_time = settings.opening_time or "09:00:00"
    closing_time = settings.closing_time or "18:00:00"

    # Convert to string if time object
    if hasattr(opening_time, "strftime"):
        opening_time = opening_time.strftime("%H:%M:%S")
    if hasattr(closing_time, "strftime"):
        closing_time = closing_time.strftime("%H:%M:%S")

    duration = int(settings.appointment_duration or 30)
    if duration <= 0:
        duration = 30

    buffer_minutes = int(settings.buffer_minutes or 0)
    if buffer_minutes < 0:
        buffer_minutes = 0

    booking_window = int(settings.booking_window_days or 60)
    if booking_window <= 0:
        booking_window = 60

    notice_minutes = int(settings.minimum_booking_notice or 15)
    if notice_minutes < 0:
        notice_minutes = 15

    return {
        "doc": settings,
        "opening_time": opening_time,
        "closing_time": closing_time,
        "duration": duration,
        "buffer_minutes": buffer_minutes,
        "booking_window": booking_window,
        "notice_minutes": notice_minutes,
    }


def _get_doctor_name(doctor):
    """Resolve a doctor identifier to its Doctor Profile name.

    Accepts a Doctor Profile id, the linked User email (case-insensitive),
    or a human display name such as "Dr. Bhagyesh" / "bhagyesh"
    (case-insensitive, optional "Dr." prefix, exact full_name first,
    then substring match).
    """
    import re as _re

    if not doctor:
        frappe.throw(_("Doctor is required"))
    key = str(doctor).strip()
    if not key:
        frappe.throw(_("Doctor is required"))

    # Direct match on Doctor Profile primary key
    if frappe.db.exists("Doctor Profile", key):
        return key

    # Match by linked User account (exact, then case-insensitive email)
    doctor_name = frappe.db.get_value("Doctor Profile", {"user": key}, "name")
    if doctor_name:
        return doctor_name
    try:
        ci = frappe.db.sql(
            "SELECT name FROM `tabDoctor Profile` WHERE LOWER(user) = LOWER(%(u)s) LIMIT 1",
            {"u": key},
            as_dict=True,
        )
        if ci:
            return ci[0]["name"]
    except Exception:
        pass

    # Human display-name match against full_name.
    cleaned = _re.sub(r"^\s*dr\.?\s+", "", key, flags=_re.IGNORECASE).strip().lower()
    if cleaned:
        try:
            rows = frappe.get_all("Doctor Profile", fields=["name", "full_name"]) or []
        except Exception:
            rows = []
        norm = {}
        for r in rows:
            full = _re.sub(r"^\s*dr\.?\s+", "", str(r.get("full_name") or ""), flags=_re.IGNORECASE).strip().lower()
            norm[r["name"]] = full
        for name, full in norm.items():
            if full and full == cleaned:
                return name
        for name, full in norm.items():
            name_l = str(name or "").lower()
            if (full and (cleaned in full or full in cleaned)) or (name_l and (cleaned in name_l or name_l in cleaned)):
                return name

    frappe.throw(_("Doctor profile not found for '{0}'").format(doctor))


def _get_patient_name(patient=None):
    """Accept a Patient Profile name, a User email, or fallback to current session."""
    user = patient or frappe.session.user

    if not user or user == "Guest":
        frappe.throw(_("Please log in to proceed"), frappe.AuthenticationError)

    # Direct match on Patient Profile primary key
    if frappe.db.exists("Patient Profile", user):
        return user

    # Match by linked User account
    patient_name = frappe.db.get_value("Patient Profile", {"user": user}, "name")
    if patient_name:
        return patient_name

    # Auto-provision Patient Profile if User account exists
    if frappe.db.exists("User", user):
        u_doc = frappe.get_doc("User", user)
        p_doc = frappe.get_doc({
            "doctype": "Patient Profile",
            "user": user,
            "full_name": u_doc.full_name or user.split("@")[0],
            "phone": u_doc.phone or u_doc.mobile_no or "",
        })
        p_doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return p_doc.name

    frappe.throw(_("Patient profile could not be resolved for '{0}'").format(user))


def _is_hospital_holiday(check_date):
    """Check weekly holidays and hospital-wide holiday dates."""
    settings_doc = frappe.get_single("Hospital Settings")
    check_date = frappe.utils.getdate(check_date)
    weekday = check_date.strftime("%A")

    weekly_holidays = [row.day for row in (settings_doc.weekly_holidays or [])]
    if weekday in weekly_holidays:
        return True

    holidays = frappe.get_all(
        "Hospital Holiday",
        filters={
            "start_date": ["<=", check_date],
            "end_date": [">=", check_date],
            "applies_to_all_doctors": 1,
        },
        pluck="name",
    )
    return bool(holidays)


def _doctor_has_leave(doctor_name, check_date, start_time, end_time):
    """Check if doctor has an approved leave or exception overlapping this interval."""
    check_date = frappe.utils.getdate(check_date)

    exceptions = frappe.get_all(
        "Doctor Availability Exception",
        filters={
            "doctor": doctor_name,
            "start_date": ["<=", check_date],
            "end_date": [">=", check_date],
            "approved": 1,
            "docstatus": ["!=", 2],
        },
        fields=["exception_type", "start_time", "end_time"],
    )

    for exc in exceptions:
        if exc.exception_type == "Full Day Leave" or (not exc.start_time and not exc.end_time):
            return True
        # Partial day leave overlap check
        e_start = frappe.utils.get_time(exc.start_time)
        e_end = frappe.utils.get_time(exc.end_time)
        if start_time < e_end and end_time > e_start:
            return True

    return False


def _slot_is_booked(doctor_name, check_date, start_time, end_time, exclude_appointment=None):
    """Check if doctor already has an active overlapping appointment."""
    check_date = frappe.utils.getdate(check_date)

    query = """
        SELECT name, appointment_time, consultation_fee
        FROM `tabAppointment`
        WHERE doctor = %(doctor)s
          AND appointment_date = %(date)s
          AND status IN ('Pending', 'Confirmed')
          AND docstatus != 2
    """
    params = {
        "doctor": doctor_name,
        "date": check_date,
    }

    if exclude_appointment:
        query += " AND name != %(exclude)s"
        params["exclude"] = exclude_appointment

    appointments = frappe.db.sql(query, params, as_dict=True)
    if not appointments:
        return False

    cfg = _get_hospital_settings()
    duration = cfg["duration"]
    buffer_min = cfg["buffer_minutes"]

    for appt in appointments:
        appt_start = frappe.utils.get_time(appt.appointment_time)
        appt_dt = datetime.combine(check_date, appt_start)
        appt_end = (appt_dt + timedelta(minutes=duration + buffer_min)).time()

        if start_time < appt_end and end_time > appt_start:
            return True

    return False


# ---------------------------------------------------------------------------
# Production-Grade Booking Validation Engine
# ---------------------------------------------------------------------------

def validate_appointment_booking(
    doctor,
    patient,
    appointment_date,
    appointment_time,
    exclude_appointment=None,
    immediate=False,
):
    """
    Comprehensive, production-grade validation for appointment booking and rescheduling.
    Validates doctor approval, date/time boundaries, hospital hours, notice, holidays,
    doctor leaves, and slot collision for both doctor and patient.

    ``immediate=True`` relaxes only the "must be in the future / notice period" rules so a
    patient physically at the reception desk can be booked for *right now* (or slotted
    earlier today). Every other rule — not-in-the-past day, hospital hours, holidays,
    doctor leave, double-booking, advance window — still applies.
    """
    # 1. Resolve & validate Doctor
    doctor_name = _get_doctor_name(doctor)
    doctor_data = frappe.db.get_value(
        "Doctor Profile",
        doctor_name,
        ["name", "user", "is_approved", "consultation_fee", "full_name"],
        as_dict=True,
    )
    if not doctor_data:
        frappe.throw(_("Doctor profile not found"))

    if not doctor_data.is_approved:
        frappe.throw(_("Dr. {0} is currently not approved for appointments").format(doctor_data.full_name or doctor_name))

    # 2. Resolve & validate Patient
    patient_name = _get_patient_name(patient)

    # 3. Parse & validate Date and Time
    try:
        apt_date = frappe.utils.getdate(appointment_date)
    except Exception:
        frappe.throw(_("Invalid appointment date format. Please use YYYY-MM-DD."))

    try:
        apt_time = frappe.utils.get_time(appointment_time)
    except Exception:
        frappe.throw(_("Invalid appointment time format. Please use HH:MM."))

    now = frappe.utils.now_datetime()
    apt_dt = datetime.combine(apt_date, apt_time)

    # 4. Past Check (Date always enforced; exact time only unless immediate walk-in)
    if apt_date < now.date():
        frappe.throw(_("Cannot book or reschedule an appointment for a past date"))
    if not immediate and apt_dt <= now:
        frappe.throw(_("Cannot book or reschedule an appointment for a past date or time"))

    # 5. Hospital Operational Settings
    cfg = _get_hospital_settings()
    duration = cfg["duration"]
    buffer_min = cfg["buffer_minutes"]
    end_time = (apt_dt + timedelta(minutes=duration)).time()

    # 6. Minimum Booking Notice (skipped for immediate walk-in / at-desk bookings)
    notice_minutes = cfg["notice_minutes"]
    if not immediate and apt_dt < now + timedelta(minutes=notice_minutes):
        frappe.throw(_("Appointments must be booked at least {0} minutes in advance").format(notice_minutes))

    # 7. Maximum Booking Window
    booking_window = cfg["booking_window"]
    max_date = now.date() + timedelta(days=booking_window)
    if apt_date > max_date:
        frappe.throw(_("Appointments can only be booked up to {0} days in advance").format(booking_window))

    # 8. Hospital Operating Hours
    open_t = frappe.utils.get_time(cfg["opening_time"])
    close_t = frappe.utils.get_time(cfg["closing_time"])

    if apt_time < open_t or end_time > close_t:
        frappe.throw(
            _("Selected time is outside hospital operational hours ({0} to {1})").format(
                cfg["opening_time"][:5], cfg["closing_time"][:5]
            )
        )

    # 9. Hospital Weekly Holiday & Calendar Holiday
    if _is_hospital_holiday(apt_date):
        frappe.throw(_("The hospital is closed for holidays on {0}").format(apt_date.strftime("%d %b %Y")))

    # 10. Doctor Leave Check
    if _doctor_has_leave(doctor_name, apt_date, apt_time, end_time):
        frappe.throw(_("Dr. {0} is on leave or unavailable at this time").format(doctor_data.full_name or doctor_name))

    # 11. Doctor Overlap Check (Double booking)
    if _slot_is_booked(doctor_name, apt_date, apt_time, end_time, exclude_appointment):
        frappe.throw(_("This slot is already reserved for another patient. Please choose a different time."))

    # 12. Patient Overlap Check (Patient cannot have two simultaneous visits)
    patient_query = """
        SELECT name, appointment_time FROM `tabAppointment`
        WHERE patient = %(patient)s
          AND appointment_date = %(date)s
          AND status IN ('Pending', 'Confirmed')
          AND docstatus != 2
    """
    p_params = {"patient": patient_name, "date": apt_date}
    if exclude_appointment:
        patient_query += " AND name != %(exclude)s"
        p_params["exclude"] = exclude_appointment

    patient_appts = frappe.db.sql(patient_query, p_params, as_dict=True)
    for pa in patient_appts:
        pa_start = frappe.utils.get_time(pa.appointment_time)
        pa_end = (datetime.combine(apt_date, pa_start) + timedelta(minutes=duration)).time()
        if apt_time < pa_end and end_time > pa_start:
            frappe.throw(_("You already have an appointment booked at this time ({0})").format(pa.appointment_time))

    return {
        "doctor_name": doctor_name,
        "doctor_data": doctor_data,
        "patient_name": patient_name,
        "appointment_date": apt_date,
        "appointment_time": apt_time,
        "end_time": end_time,
        "duration": duration,
        "consultation_fee": doctor_data.consultation_fee or 0,
    }


# ---------------------------------------------------------------------------
# Public APIs
# ---------------------------------------------------------------------------

@frappe.whitelist(allow_guest=True)
def list_appointment(patient=None):
    """
    Return appointments for a patient.
    Accepts patient profile name, user email, or resolves from authenticated session.
    Enriched with doctor profile details, clinical diagnosis, and notes.
    """
    user = patient or frappe.session.user
    if not user or user == "Guest":
        return []

    # Get patient profile candidates
    patient_profiles = frappe.get_all(
        "Patient Profile",
        filters={"user": user},
        pluck="name",
    )
    if user not in patient_profiles:
        patient_profiles.append(user)

    appointments = frappe.db.sql(
        """
        SELECT
            a.name,
            a.patient,
            a.doctor,
            a.slot,
            a.appointment_date,
            a.appointment_time,
            a.status,
            a.reason,
            a.consultation_fee,
            a.payment_status,
            a.created_at,
            a.symptoms,
            a.diagnosis,
            a.consultation_notes,
            a.treatment_plan,
            a.follow_up_date,
            d.full_name       AS doctor_name,
            d.specialty       AS doctor_specialty,
            d.profile_image   AS doctor_image,
            d.phone           AS doctor_phone,
            pp.full_name      AS patient_name,
            pp.phone          AS patient_phone
        FROM `tabAppointment` a
        LEFT JOIN `tabDoctor Profile` d  ON d.name = a.doctor
        LEFT JOIN `tabPatient Profile` pp ON pp.name = a.patient
        WHERE (a.patient IN %(patients)s OR pp.user = %(user)s)
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
        """,
        {"patients": tuple(patient_profiles), "user": user},
        as_dict=True,
    )

    return appointments


@frappe.whitelist(allow_guest=True)
def show_appointment(appointment_id):
    """
    Return comprehensive appointment details matching either name or slot.
    Includes full doctor profile, patient profile, clinical diagnosis, and prescriptions.
    """
    if not appointment_id:
        frappe.throw(_("Appointment ID is required"))

    # Match by name or slot
    appt = frappe.db.sql(
        """
        SELECT
            a.name,
            a.patient,
            a.doctor,
            a.slot,
            a.appointment_date,
            a.appointment_time,
            a.status,
            a.reason,
            a.consultation_fee,
            a.payment_status,
            a.created_at,
            a.symptoms,
            a.diagnosis,
            a.consultation_notes,
            a.treatment_plan,
            a.follow_up_date,
            a.follow_up_instructions,
            a.referral,
            a.visit_stage,
            a.queue_token,
            a.priority,
            a.checked_in,
            a.checked_in_at,
            a.called_at
        FROM `tabAppointment` a
        WHERE a.name = %(id)s OR a.slot = %(id)s
        LIMIT 1
        """,
        {"id": appointment_id},
        as_dict=True,
    )

    if not appt:
        frappe.throw(_("Appointment '{0}' not found").format(appointment_id), frappe.DoesNotExistError)

    appt_data = appt[0]

    # Fetch Doctor Details
    doctor_data = None
    if appt_data.doctor:
        doctor_data = frappe.db.get_value(
            "Doctor Profile",
            appt_data.doctor,
            [
                "name", "user", "full_name", "specialty", "qualification",
                "experience_years", "consultation_fee", "bio", "profile_image",
                "rating", "phone"
            ],
            as_dict=True,
        )

    # Fetch Patient Details
    patient_data = None
    if appt_data.patient:
        patient_data = frappe.db.get_value(
            "Patient Profile",
            appt_data.patient,
            ["name", "user", "full_name", "phone", "age", "gender"],
            as_dict=True,
        )

    # Fetch Prescriptions & Medicines linked to this appointment
    prescriptions = frappe.db.sql(
        """
        SELECT
            p.name,
            p.prescription_date,
            p.diagnosis,
            p.instructions,
            p.follow_up_date,
            p.status,
            p.notes
        FROM `tabPrescription` p
        WHERE p.appointment = %(name)s
        ORDER BY p.creation DESC
        """,
        {"name": appt_data.name},
        as_dict=True,
    )

    for prx in prescriptions:
        prx["medicines"] = frappe.db.sql(
            """
            SELECT
                pm.name,
                pm.prescribed_medicine_name,
                pm.medicine,
                pm.dosage,
                pm.frequency,
                pm.route,
                pm.start_date,
                pm.end_date,
                pm.dose_time_1,
                pm.dose_time_2,
                pm.dose_time_3,
                pm.dose_time_4,
                pm.instructions,
                pm.status
            FROM `tabPrescription Medicine` pm
            WHERE pm.prescription = %(prx)s
            ORDER BY pm.creation ASC
            """,
            {"prx": prx.name},
            as_dict=True,
        )

    # Fetch reports linked to this appointment OR shared across its referral episode
    report_fields = [
        "name", "appointment", "referral", "ordered_by", "report_type", "title",
        "laboratory", "external", "status", "report_file", "findings", "description",
        "uploaded_by", "uploaded_at", "reviewed_by", "reviewed_at", "creation",
    ]
    if appt_data.referral:
        reports = frappe.get_all(
            "Patient Report",
            or_filters=[["appointment", "=", appt_data.name], ["referral", "=", appt_data.referral]],
            fields=report_fields,
            order_by="creation desc",
        )
    else:
        reports = frappe.get_all(
            "Patient Report",
            filters={"appointment": appt_data.name},
            fields=report_fields,
            order_by="creation desc",
        )

    # Shared referral episode (both doctors + the other linked appointment)
    referral_data = None
    if appt_data.referral:
        referral_data = frappe.get_all(
            "Referral",
            filters={"name": appt_data.referral},
            fields=[
                "name", "patient", "referring_doctor", "referred_to_doctor", "specialty",
                "source_appointment", "target_appointment", "status", "reason",
                "clinical_notes", "referral_date",
            ],
            limit=1,
        )
        referral_data = referral_data[0] if referral_data else None

    return {
        **appt_data,
        "doctor_info": doctor_data,
        "patient_info": patient_data,
        "prescriptions": prescriptions,
        "reports": reports,
        "referral": referral_data,
    }


@frappe.whitelist(allow_guest=True)
def create_appointment(
    patient,
    doctor,
    appointment_date,
    appointment_time,
    reason=None,
    symptoms=None,
):
    """
    Create a new appointment with strict production-grade validations.
    """
    val = validate_appointment_booking(
        doctor=doctor,
        patient=patient,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
    )

    # Create slot record
    slot_doc = frappe.get_doc({
        "doctype": "Availability Slot",
        "doctor": val["doctor_name"],
        "date": val["appointment_date"],
        "start_time": val["appointment_time"],
        "end_time": val["end_time"],
        "is_booked": 1,
    })
    slot_doc.insert(ignore_permissions=True)

    # Create Appointment
    appt_doc = frappe.get_doc({
        "doctype": "Appointment",
        "patient": val["patient_name"],
        "doctor": val["doctor_name"],
        "slot": slot_doc.name,
        "appointment_date": val["appointment_date"],
        "appointment_time": val["appointment_time"],
        "status": "Pending",
        "reason": reason or "",
        "symptoms": symptoms or "",
        "consultation_fee": val["consultation_fee"],
        "payment_status": "Pending",
        "created_at": frappe.utils.now_datetime(),
    })
    appt_doc.insert(ignore_permissions=True)

    frappe.db.commit()

    return {
        "success": True,
        "message": _("Appointment booked successfully"),
        "name": appt_doc.name,
        "slot": slot_doc.name,
    }


@frappe.whitelist()
def book_appointment(doctor, date, time, reason=None, symptoms=None):
    """Session-authenticated patient booking shortcut."""
    if frappe.session.user == "Guest":
        frappe.throw(_("Please log in to book an appointment"), frappe.AuthenticationError)

    patient_name = _get_patient_name()
    return create_appointment(
        patient=patient_name,
        doctor=doctor,
        appointment_date=date,
        appointment_time=time,
        reason=reason,
        symptoms=symptoms,
    )


@frappe.whitelist()
def update_appointment(
    appointment_id,
    appointment_date=None,
    appointment_time=None,
    reason=None,
    symptoms=None,
):
    """
    Reschedule date/time or update clinical details for an existing appointment.
    Performs full validation against doctor schedules, hospital hours, and slot conflicts.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Please log in first"), frappe.AuthenticationError)

    appt = frappe.db.get_value(
        "Appointment",
        {"name": appointment_id},
        ["name", "patient", "doctor", "slot", "appointment_date", "appointment_time", "status"],
        as_dict=True,
    )
    if not appt:
        # Check by slot
        by_slot = frappe.db.get_value("Appointment", {"slot": appointment_id}, "name")
        if by_slot:
            return update_appointment(by_slot, appointment_date, appointment_time, reason, symptoms)
        frappe.throw(_("Appointment '{0}' not found").format(appointment_id), frappe.DoesNotExistError)

    if appt.status in ["Completed", "Cancelled"]:
        frappe.throw(_("Cannot edit an appointment that is already {0}").format(appt.status))

    # Authorization
    roles = frappe.get_roles(frappe.session.user)
    is_admin = "System Manager" in roles
    if not is_admin:
        p_name = _get_patient_name()
        d_name = frappe.db.get_value("Doctor Profile", {"user": frappe.session.user}, "name")
        if appt.patient != p_name and appt.doctor != d_name:
            frappe.throw(_("You are not authorized to edit this appointment"), frappe.PermissionError)

    doc = frappe.get_doc("Appointment", appt.name)

    # Handle Rescheduling
    new_date = appointment_date or doc.appointment_date
    new_time = appointment_time or doc.appointment_time

    date_or_time_changed = (
        str(new_date) != str(doc.appointment_date) or
        str(new_time)[:5] != str(doc.appointment_time)[:5]
    )

    if date_or_time_changed:
        val = validate_appointment_booking(
            doctor=doc.doctor,
            patient=doc.patient,
            appointment_date=new_date,
            appointment_time=new_time,
            exclude_appointment=doc.name,
        )

        # Free old slot
        if doc.slot and frappe.db.exists("Availability Slot", doc.slot):
            frappe.db.set_value("Availability Slot", doc.slot, "is_booked", 0)

        # Create new slot
        new_slot = frappe.get_doc({
            "doctype": "Availability Slot",
            "doctor": doc.doctor,
            "date": val["appointment_date"],
            "start_time": val["appointment_time"],
            "end_time": val["end_time"],
            "is_booked": 1,
        })
        new_slot.insert(ignore_permissions=True)

        doc.appointment_date = val["appointment_date"]
        doc.appointment_time = val["appointment_time"]
        doc.slot = new_slot.name

    if reason is not None:
        doc.reason = reason
    if symptoms is not None:
        doc.symptoms = symptoms

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "success": True,
        "message": _("Appointment updated successfully"),
        "name": doc.name,
        "appointment_date": doc.appointment_date,
        "appointment_time": doc.appointment_time,
        "slot": doc.slot,
    }


@frappe.whitelist()
def cancel_appointment(appointment_id, reason=None):
    """
    Cancel an appointment and free its availability slot.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Please log in first"), frappe.AuthenticationError)

    appt = frappe.db.get_value(
        "Appointment",
        {"name": appointment_id},
        ["name", "patient", "doctor", "slot", "status"],
        as_dict=True,
    )
    if not appt:
        by_slot = frappe.db.get_value("Appointment", {"slot": appointment_id}, "name")
        if by_slot:
            return cancel_appointment(by_slot, reason)
        frappe.throw(_("Appointment not found"), frappe.DoesNotExistError)

    if appt.status == "Cancelled":
        return {"success": True, "message": _("Appointment is already cancelled")}

    # Authorization
    roles = frappe.get_roles(frappe.session.user)
    is_admin = "System Manager" in roles
    if not is_admin:
        p_name = _get_patient_name()
        d_name = frappe.db.get_value("Doctor Profile", {"user": frappe.session.user}, "name")
        if appt.patient != p_name and appt.doctor != d_name:
            frappe.throw(_("You are not authorized to cancel this appointment"), frappe.PermissionError)

    doc = frappe.get_doc("Appointment", appt.name)
    doc.status = "Cancelled"
    if reason:
        doc.reason = f"{doc.reason or ''} (Cancelled: {reason})".strip()
    doc.save(ignore_permissions=True)

    # Free availability slot
    if doc.slot and frappe.db.exists("Availability Slot", doc.slot):
        frappe.db.set_value("Availability Slot", doc.slot, "is_booked", 0)

    # Cancel any pending medicine reminders for this appointment
    frappe.db.sql(
        """
        UPDATE `tabMedicine Reminder`
        SET reminder_status = 'Cancelled', active = 0
        WHERE prescription IN (
            SELECT name FROM `tabPrescription` WHERE appointment = %(name)s
        ) AND reminder_status = 'Pending'
        """,
        {"name": doc.name},
    )

    frappe.db.commit()

    return {
        "success": True,
        "message": _("Appointment cancelled successfully"),
        "name": doc.name,
        "status": "Cancelled",
    }


@frappe.whitelist()
def delete_appointment(appointment_id):
    """
    Permanently delete an appointment.
    Completed consultations cannot be deleted for medical compliance.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Please log in first"), frappe.AuthenticationError)

    appt = frappe.db.get_value(
        "Appointment",
        {"name": appointment_id},
        ["name", "patient", "doctor", "slot", "status"],
        as_dict=True,
    )
    if not appt:
        by_slot = frappe.db.get_value("Appointment", {"slot": appointment_id}, "name")
        if by_slot:
            return delete_appointment(by_slot)
        frappe.throw(_("Appointment not found"), frappe.DoesNotExistError)

    if appt.status == "Completed":
        frappe.throw(_("Completed clinical consultation records cannot be deleted for legal audit trail compliance."))

    # Authorization
    roles = frappe.get_roles(frappe.session.user)
    is_admin = "System Manager" in roles
    if not is_admin:
        p_name = _get_patient_name()
        d_name = frappe.db.get_value("Doctor Profile", {"user": frappe.session.user}, "name")
        if appt.patient != p_name and appt.doctor != d_name:
            frappe.throw(_("You are not authorized to delete this appointment"), frappe.PermissionError)

    # Free slot
    if appt.slot and frappe.db.exists("Availability Slot", appt.slot):
        frappe.db.set_value("Availability Slot", appt.slot, "is_booked", 0)

    frappe.delete_doc("Appointment", appt.name, ignore_permissions=True)
    frappe.db.commit()

    return {
        "success": True,
        "message": _("Appointment deleted successfully"),
        "name": appt.name,
    }


@frappe.whitelist()
def update_appointment_status(appointment_id, status):
    """
    Update appointment status (Pending, Confirmed, Completed, Cancelled).
    Frees availability slot if status becomes Cancelled.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Please log in first"), frappe.AuthenticationError)

    valid_statuses = ["Pending", "Confirmed", "Completed", "Cancelled"]
    if status not in valid_statuses:
        frappe.throw(_("Invalid status. Must be one of: {0}").format(", ".join(valid_statuses)))

    if status == "Cancelled":
        return cancel_appointment(appointment_id)

    doc_name = appointment_id
    if not frappe.db.exists("Appointment", doc_name):
        doc_name = frappe.db.get_value("Appointment", {"slot": appointment_id}, "name")
        if not doc_name:
            frappe.throw(_("Appointment not found"))

    doc = frappe.get_doc("Appointment", doc_name)
    doc.status = status
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {"name": doc.name, "status": doc.status, "success": True}


@frappe.whitelist()
def get_available_slots(doctor, date, exclude_appointment=None):
    """
    Generate available appointment slots for one doctor and date.
    Respects hospital working hours, holidays, doctor leaves, and existing bookings.
    ``exclude_appointment`` frees the caller's own slot so reschedules can reuse it.
    """
    doctor_name = _get_doctor_name(doctor)
    date_val = frappe.utils.getdate(date)
    today = frappe.utils.getdate()

    if date_val < today:
        return []

    cfg = _get_hospital_settings()
    booking_window = cfg["booking_window"]
    if date_val > today + timedelta(days=booking_window):
        return []

    if not frappe.db.get_value("Doctor Profile", doctor_name, "is_approved"):
        return []

    if _is_hospital_holiday(date_val):
        return []

    open_t = frappe.utils.get_time(cfg["opening_time"])
    close_t = frappe.utils.get_time(cfg["closing_time"])
    duration = cfg["duration"]
    buffer_min = cfg["buffer_minutes"]
    step = timedelta(minutes=duration + buffer_min)

    now = frappe.utils.now_datetime()
    notice_min = cfg["notice_minutes"]

    slots = []
    current_dt = datetime.combine(date_val, open_t)
    closing_dt = datetime.combine(date_val, close_t)

    while current_dt + timedelta(minutes=duration) <= closing_dt:
        slot_start = current_dt.time()
        slot_end = (current_dt + timedelta(minutes=duration)).time()

        # Notice check for today
        if current_dt >= now + timedelta(minutes=notice_min):
            # Check leave & booked
            is_leave = _doctor_has_leave(doctor_name, date_val, slot_start, slot_end)
            is_booked = _slot_is_booked(
                doctor_name, date_val, slot_start, slot_end,
                exclude_appointment=exclude_appointment)

            if not is_leave and not is_booked:
                slots.append({
                    "start_time": slot_start.strftime("%H:%M:%S"),
                    "end_time": slot_end.strftime("%H:%M:%S"),
                    "formatted": slot_start.strftime("%I:%M %p"),
                })

        current_dt += step

    return slots


# ---------------------------------------------------------------------------
# Database Maintenance Routine
# ---------------------------------------------------------------------------

@frappe.whitelist()
def cleanup_old_records():
    """
    Clean old, broken, and orphaned records that break flow in DocBook.
    - Updates Hospital Settings with production operational defaults.
    - Resets is_booked on Availability Slot if linked appointment is cancelled/deleted.
    - Fixes broken patient/doctor references.
    """
    # 1. Hospital Settings
    doc = frappe.get_single("Hospital Settings")
    doc.opening_time = "09:00:00"
    doc.closing_time = "18:00:00"
    doc.appointment_duration = 30
    doc.buffer_minutes = 0
    doc.booking_window_days = 60
    doc.minimum_booking_notice = 15
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()

    # 2. Availability Slots cleanup
    slots = frappe.get_all(
        "Availability Slot",
        fields=["name", "doctor", "start_time", "end_time", "is_booked"]
    )
    cleaned_slots = 0
    for s in slots:
        has_active = frappe.db.exists(
            "Appointment",
            {
                "slot": s.name,
                "status": ["in", ["Pending", "Confirmed"]],
                "docstatus": ["!=", 2],
            }
        )
        should_be_booked = 1 if has_active else 0
        if s.is_booked != should_be_booked:
            frappe.db.set_value("Availability Slot", s.name, "is_booked", should_be_booked)
            cleaned_slots += 1

    # 3. Clean broken appointments
    appts = frappe.get_all("Appointment", fields=["name", "patient", "doctor", "status"])
    cleaned_appts = 0
    for a in appts:
        d_exists = frappe.db.exists("Doctor Profile", a.doctor) or frappe.db.exists("User", a.doctor)
        p_exists = frappe.db.exists("Patient Profile", a.patient) or frappe.db.exists("User", a.patient)
        if not d_exists or not p_exists:
            frappe.delete_doc("Appointment", a.name, ignore_permissions=True)
            cleaned_appts += 1

    frappe.db.commit()

    return {
        "success": True,
        "message": _("Database cleanup completed successfully"),
        "slots_fixed": cleaned_slots,
        "broken_appointments_removed": cleaned_appts,
        "hospital_hours": "09:00:00 - 18:00:00",
    }