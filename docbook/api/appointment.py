"""
DocBook Appointment API
Production-grade validations, scheduling, slot management, and full lifecycle operations.
"""

from datetime import datetime, date, time, timedelta
import frappe
from frappe import _

from docbook.api.access import require_login, current_patient


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
            a.follow_up_instructions,
            a.qr_code,
            a.checked_in,
            a.queue_token,
            a.visit_stage,
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
            a.called_at,
            a.qr_code,
            a.fast_track,
            a.ai_priority
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

    # Pre-generate or load base64 QR data URL for upcoming/active appointments
    qr_data_url = None
    if appt_data.status not in ("Completed", "Cancelled"):
        try:
            import qrcode, base64
            from io import BytesIO
            qr_data = f"DOCBOOK|APT|{appt_data['name']}|{appt_data['patient']}|{appt_data['doctor']}|{appt_data['appointment_date']}|{appt_data['appointment_time']}"
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(qr_data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = BytesIO()
            img.save(buf)
            raw_bytes = buf.getvalue()
            qr_data_url = f"data:image/png;base64,{base64.b64encode(raw_bytes).decode('ascii')}"

            # If qr_code file URL missing, also create File record
            if not appt_data.get("qr_code"):
                file_doc = frappe.get_doc({
                    "doctype": "File",
                    "file_name": f"QR-{appt_data['name']}.png",
                    "content": raw_bytes,
                    "is_private": 0,
                })
                file_doc.save(ignore_permissions=True)
                frappe.db.set_value("Appointment", appt_data["name"], "qr_code", file_doc.file_url)
                frappe.db.commit()
                appt_data["qr_code"] = file_doc.file_url
        except Exception:
            pass

    return {
        **appt_data,
        "qr_data_url": qr_data_url,
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


# ---------------------------------------------------------------------------
# Referral-Aware Appointment Booking
# ---------------------------------------------------------------------------

def _resolve_patient(patient):
    if not patient:
        frappe.throw(_("Patient is required"))
    key = str(patient).strip()
    if frappe.db.exists("Patient Profile", key):
        return key
    patient_name = frappe.db.get_value("Patient Profile", {"user": key}, "name")
    if patient_name:
        return patient_name
    frappe.throw(_("Patient '{0}' not found").format(patient))


def _is_slot_blocked_for_referral(doctor_name, date_val, time_val, exclude_appointment=None):
    filters = {
        "doctor": doctor_name,
        "appointment_date": date_val,
        "appointment_time": time_val,
        "status": ["in", ["Pending", "Confirmed"]],
        "docstatus": ["!=", 2],
    }
    if exclude_appointment:
        filters["name"] = ["!=", exclude_appointment]
    rows = frappe.get_all("Appointment", filters=filters, fields=["name", "referral_type", "fast_track"])
    for r in rows:
        if r.referral_type in ("Referral", "Fast Track Referral") or r.fast_track:
            return True, r.name
    return False, None


@frappe.whitelist()
def create_referral_appointment(
    patient,
    referring_doctor,
    referred_to_doctor,
    referral_type="Referral",
    appointment_date=None,
    appointment_time=None,
    reason=None,
    symptoms=None,
    clinical_notes=None,
):
    require_login()

    patient_name = _resolve_patient(patient)

    referred_name = frappe.db.get_value(
        "Doctor Profile", {"user": referred_to_doctor}, "name"
    ) or (referred_to_doctor if frappe.db.exists("Doctor Profile", referred_to_doctor) else None)
    if not referred_name:
        frappe.throw(_("Referred doctor '{0}' not found").format(referred_to_doctor))

    referring_name = frappe.db.get_value(
        "Doctor Profile", {"user": referring_doctor}, "name"
    ) or (referring_doctor if frappe.db.exists("Doctor Profile", referring_doctor) else None)
    if not referring_name:
        frappe.throw(_("Referring doctor '{0}' not found").format(referring_doctor))

    user_roles = frappe.get_roles(frappe.session.user)
    is_admin = "System Manager" in user_roles
    is_receptionist = "Receptionist" in user_roles
    if not is_admin and not is_receptionist and referring_name != _current_doctor_profile():
        frappe.throw(_("Only the referring doctor can create this referral appointment"))

    if referral_type not in ("Regular Checkup", "Referral", "Fast Track Referral"):
        frappe.throw(_("Invalid referral type"))

    if appointment_date and appointment_time:
        from docbook.api.appointment import validate_appointment_booking

        val = validate_appointment_booking(
            doctor=referred_name,
            patient=patient_name,
            appointment_date=frappe.utils.getdate(appointment_date),
            appointment_time=frappe.utils.get_time(appointment_time),
        )

        if referral_type in ("Referral", "Fast Track Referral"):
            blocked, blocker = _is_slot_blocked_for_referral(
                referred_name, val["appointment_date"], val["appointment_time"]
            )
            if blocked:
                frappe.throw(
                    _("Slot {0} is already reserved for another referral appointment ({1})").format(
                        val["appointment_time"], blocker
                    )
                )

        appt = frappe.get_doc({
            "doctype": "Appointment",
            "patient": patient_name,
            "doctor": referred_name,
            "appointment_date": val["appointment_date"],
            "appointment_time": val["appointment_time"],
            "status": "Confirmed",
            "reason": reason or "Referred appointment",
            "symptoms": symptoms or "",
            "referral_type": referral_type,
            "fast_track": 1 if referral_type == "Fast Track Referral" else 0,
            "ai_priority": "High" if referral_type == "Fast Track Referral" else "Medium",
            "created_at": frappe.utils.now_datetime(),
        })
        appt.insert(ignore_permissions=True)
        frappe.db.commit()

        ref_name = None
        if clinical_notes or reason:
            try:
                ref = frappe.get_doc({
                    "doctype": "Referral",
                    "patient": patient_name,
                    "referring_doctor": referring_name,
                    "referred_to_doctor": referred_name,
                    "referral_type": referral_type,
                    "source_appointment": None,
                    "target_appointment": appt.name,
                    "status": "Pending",
                    "reason": reason or "Referred appointment",
                    "clinical_notes": clinical_notes or "",
                    "referral_date": frappe.utils.now_datetime(),
                })
                ref.insert(ignore_permissions=True)
                frappe.db.commit()
                ref_name = ref.name
            except Exception:
                ref_name = None

        return {
            "success": True,
            "appointment": appt.name,
            "patient": patient_name,
            "doctor": referred_name,
            "referral": ref_name,
            "referral_type": referral_type,
            "fast_track": appt.fast_track,
            "ai_priority": appt.ai_priority,
            "appointment_date": str(appt.appointment_date),
            "appointment_time": str(appt.appointment_time)[:5],
            "message": _("Referral appointment booked and slot reserved"),
        }

    frappe.throw(_("Appointment date and time are required"))


def _current_doctor_profile():
    return frappe.db.get_value("Doctor Profile", {"user": frappe.session.user}, "name")


@frappe.whitelist()
def generate_qr_code(appointment_id):
    require_login()

    appt = frappe.db.get_value(
        "Appointment", appointment_id,
        ["name", "patient", "doctor", "appointment_date", "appointment_time", "qr_code"],
        as_dict=True,
    )
    if not appt:
        frappe.throw(_("Appointment not found"), frappe.DoesNotExistError)

    user_roles = frappe.get_roles(frappe.session.user)
    is_admin = "System Manager" in user_roles
    is_receptionist = "Receptionist" in user_roles
    patient_name = current_patient()
    if not is_admin and not is_receptionist:
        if patient_name != appt.patient:
            doctor_profile = _current_doctor_profile()
            if doctor_profile != appt.doctor:
                frappe.throw(_("Not authorized to access this appointment"), frappe.PermissionError)

    import qrcode
    from io import BytesIO

    qr_data = f"DOCBOOK|APT|{appt['name']}|{appt['patient']}|{appt['doctor']}|{appt['appointment_date']}|{appt['appointment_time']}"

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    import base64
    buf = BytesIO()
    img.save(buf)
    raw_bytes = buf.getvalue()
    b64_str = base64.b64encode(raw_bytes).decode("ascii")
    data_url = f"data:image/png;base64,{b64_str}"

    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": f"QR-{appt['name']}.png",
        "content": raw_bytes,
        "is_private": 0,
    })
    file_doc.save(ignore_permissions=True)
    frappe.db.commit()

    frappe.db.set_value("Appointment", appointment_id, "qr_code", file_doc.file_url)
    frappe.db.commit()

    return {
        "success": True,
        "appointment": appointment_id,
        "qr_code": file_doc.file_url,
        "qr_data_url": data_url,
        "qr_data": qr_data,
        "message": _("QR code generated successfully"),
    }


# Canonical specialty synonyms — AI must pick ONLY from these options.
# Keys are user-facing terms/symptoms/synonyms; values are canonical specialty names.
# Order matters: more specific/specialty terms should come before general ones.
_SPECIALTY_SYNONYMS = {
    # --- Cardiology ---
    "cardiologist": "cardiology",
    "heart": "cardiology",
    "cardiac": "cardiology",
    "chest pain": "cardiology",
    "heart attack": "cardiology",
    "palpitations": "cardiology",
    "irregular heartbeat": "cardiology",
    "hypertension": "cardiology",
    "high blood pressure": "cardiology",
    "angina": "cardiology",
    "shortness of breath": "cardiology",
    "leg swelling": "cardiology",
    "edema": "cardiology",
    # --- Dermatology ---
    "dermatologist": "dermatology",
    "skin": "dermatology",
    "rash": "dermatology",
    "acne": "dermatology",
    "eczema": "dermatology",
    "psoriasis": "dermatology",
    "mole": "dermatology",
    "skin cancer": "dermatology",
    "itching": "dermatology",
    "hives": "dermatology",
    "dermatitis": "dermatology",
    "wart": "dermatology",
    "hair loss": "dermatology",
    "sunburn": "dermatology",
    "blister": "dermatology",
    # --- Orthopedics ---
    "orthopedic": "orthopedics",
    "ortho": "orthopedics",
    "bone": "orthopedics",
    "fracture": "orthopedics",
    "broken bone": "orthopedics",
    "sprain": "orthopedics",
    "strain": "orthopedics",
    "arthritis": "orthopedics",
    "back pain": "orthopedics",
    "joint pain": "orthopedics",
    "knee pain": "orthopedics",
    "shoulder pain": "orthopedics",
    "neck pain": "orthopedics",
    "muscle pain": "orthopedics",
    "sports injury": "orthopedics",
    "torn ligament": "orthopedics",
    "tendonitis": "orthopedics",
    # --- Pediatrics ---
    "pediatrician": "pediatrics",
    "pediatrics": "pediatrics",
    "child": "pediatrics",
    "baby": "pediatrics",
    "infant": "pediatrics",
    "toddler": "pediatrics",
    "newborn": "pediatrics",
    "child fever": "pediatrics",
    "childhood illness": "pediatrics",
    "vaccination": "pediatrics",
    # --- Dentist ---
    "dentist": "dentist",
    "dental": "dentist",
    "teeth": "dentist",
    "tooth": "dentist",
    "orthodontist": "dentist",
    "toothache": "dentist",
    "dental pain": "dentist",
    "gum bleeding": "dentist",
    "wisdom tooth": "dentist",
    "cavity": "dentist",
    "root canal": "dentist",
    "mouth ulcer": "dentist",
    "jaw pain": "dentist",
    "tooth decay": "dentist",
    "gum disease": "dentist",
    # --- General Physician (fallback for truly general symptoms) ---
    "general": "general physician",
    "physician": "general physician",
    "gp": "general physician",
    "fever": "general physician",
    "cold": "general physician",
    "flu": "general physician",
    "headache": "general physician",
    "cough": "general physician",
    "sore throat": "general physician",
    "stomach pain": "general physician",
    "fatigue": "general physician",
    "nausea": "general physician",
    "vomiting": "general physician",
    "diarrhea": "general physician",
    "constipation": "general physician",
    "allergy": "general physician",
    "infection": "general physician",
    "migraine": "general physician",
    "dizziness": "general physician",
    "checkup": "general physician",
}

# Deduplicated canonical specialty values the AI is allowed to return.
_VALID_SPECIALTIES = sorted(set(_SPECIALTY_SYNONYMS.values()))

_SYNONYM_KEYS_LOWER = {k.lower(): v for k, v in _SPECIALTY_SYNONYMS.items()}


def _normalize_specialty(raw: str) -> str | None:
    """Map a raw specialty string to a canonical value via synonyms, or None."""
    key = raw.strip().lower()
    return _SYNONYM_KEYS_LOWER.get(key)


@frappe.whitelist()
def _query_ollama(symptoms: str) -> dict:
    """
    Query local Ollama (qwen2.5:7b) to analyse symptoms and suggest
    relevant medical specialties. The AI is constrained to pick ONLY from
    the predefined _SPECIALTY_SYNONYMS options — it cannot invent specialties.
    Falls back to keyword matching if Ollama is unavailable or returns an error.
    """
    import json as _json
    import urllib.request as _req
    import urllib.error as _err

    valid_list = ", ".join(_VALID_SPECIALTIES)

    prompt = (
        "You are a medical triage assistant. Given the patient symptoms below, "
        "select the MOST relevant medical specialty (one or more) STRICTLY from this "
        f"allowed list: {valid_list}. Do NOT invent any specialty outside this list.\n"
        "Mapping guidance: chest pain/heart palpitations/high blood pressure -> cardiology; "
        "rash/acne/eczema/itching/skin lesions -> dermatology; "
        "fracture/back pain/joint pain/knee pain/arthritis/sports injury -> orthopedics; "
        "child/baby/infant/toddler/pediatric/vaccination -> pediatrics; "
        "toothache/gum bleeding/cavity/wisdom tooth/jaw pain -> dentist; "
        "fever/cold/flu/headache/cough/sore throat/stomach pain/general checkup -> general physician. "
        "If symptoms clearly point to a specific specialty, prefer that over general physician. "
        "Also estimate urgency (low/medium/high/critical). "
        "Reply ONLY in JSON format with keys: specialties (array of strings from the "
        "allowed list only), urgency (string), reasoning (short string).\n\n"
        f"Symptoms: {symptoms}"
    )

    payload = _json.dumps(
        {
            "model": "qwen2.5:7b",
            "prompt": prompt,
            "stream": False,
            "temperature": 0.3,
        }
    ).encode("utf-8")

    try:
        request = _req.Request(
            "http://localhost:11434/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with _req.urlopen(request, timeout=15) as response:
            raw = response.read().decode("utf-8")
            result = _json.loads(raw)
            text = result.get("response", "{}")
            # Ollama may wrap JSON in code fences; strip them
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            parsed = _json.loads(text)
            raw_specialties = parsed.get("specialties", [])

            # Normalize each returned specialty through the synonyms map.
            # Drop anything that doesn't map to a known canonical value.
            normalized = []
            for s in raw_specialties:
                canon = _normalize_specialty(s)
                if canon and canon not in normalized:
                    normalized.append(canon)

            if not normalized:
                # AI returned nothing usable — fall through to keyword matching.
                raise ValueError("No valid specialties returned by Ollama")

            return {
                "specialties": normalized,
                "urgency": parsed.get("urgency", "medium"),
                "reasoning": parsed.get("reasoning", ""),
            }
    except Exception:
        pass

    # Fallback: keyword-based matching using the synonyms map.
    symptoms_lower = symptoms.lower()
    matched_specialties = []
    for synonym_key, canonical in _SPECIALTY_SYNONYMS.items():
        if synonym_key in symptoms_lower and canonical not in matched_specialties:
            matched_specialties.append(canonical)

    if not matched_specialties:
        matched_specialties = ["general physician"]

    urgency = "medium"
    critical_keywords = ["chest pain", "stroke", "seizure", "difficulty breathing", "severe"]
    if any(kw in symptoms_lower for kw in critical_keywords):
        urgency = "critical"

    return {
        "specialties": matched_specialties,
        "urgency": urgency,
        "reasoning": "AI matched your symptoms to the most relevant specialist.",
    }


@frappe.whitelist()
def ai_assign_doctor(symptoms, preferred_date=None, preferred_time=None):
    require_login()

    if not symptoms or not str(symptoms).strip():
        frappe.throw(_("Symptoms are required"))

    # Query Ollama for specialty + urgency analysis
    ai_result = _query_ollama(symptoms)
    matched_specialties = ai_result.get("specialties", ["general physician"])
    ai_urgency = ai_result.get("urgency", "medium")
    ai_reasoning = ai_result.get("reasoning", "")

    doctors = frappe.get_all(
        "Doctor Profile",
        filters={
            "specialty": ["in", matched_specialties],
            "is_approved": 1,
        },
        fields=["name", "user", "full_name", "specialty", "rating", "consultation_fee"],
        order_by="rating desc",
    )

    # Map urgency to ai_priority
    priority_map = {"low": "Low", "medium": "Medium", "high": "High", "critical": "Critical"}
    ai_priority = priority_map.get(ai_urgency, "Medium")

    if not doctors:
        return {
            "success": True,
            "symptoms": symptoms,
            "ai_reasoning": ai_reasoning,
            "ai_urgency": ai_urgency,
            "ai_priority": ai_priority,
            "assigned_doctor": None,
            "recommended_slot": None,
            "matched_specialties": matched_specialties,
            "doctors_available": False,
            "message": _("No doctors available for your symptoms"),
        }

    from docbook.api.appointment import get_available_slots

    target_date = preferred_date or frappe.utils.getdate()

    # Sort doctors: critical urgency gets first available slot across all matched doctors
    best_doctor = None
    best_slot = None

    for d in doctors:
        slots = get_available_slots(doctor=d["user"], date=str(target_date))
        if slots:
            best_doctor = d
            best_slot = slots[0]
            break

    if not best_doctor:
        frappe.throw(_("No available slots for matched doctors on the selected date"))

    return {
        "success": True,
        "symptoms": symptoms,
        "ai_reasoning": ai_reasoning,
        "ai_urgency": ai_urgency,
        "ai_priority": ai_priority,
        "assigned_doctor": {
            "name": best_doctor["name"],
            "full_name": best_doctor["full_name"],
            "specialty": best_doctor["specialty"],
            "rating": best_doctor.get("rating"),
            "consultation_fee": best_doctor.get("consultation_fee"),
        },
        "recommended_slot": best_slot,
        "matched_specialties": matched_specialties,
        "message": _("Doctor assigned based on your symptoms"),
    }


@frappe.whitelist()
def get_patient_appointment_history(patient=None):
    require_login()

    user_roles = frappe.get_roles(frappe.session.user)
    is_admin = "System Manager" in user_roles
    is_receptionist = "Receptionist" in user_roles
    is_doctor = bool(_current_doctor_profile())

    if not is_admin and not is_receptionist and not is_doctor:
        frappe.throw(_("Not authorized"), frappe.PermissionError)

    if patient:
        patient_name = _resolve_patient(patient)
    else:
        patient_name = current_patient()
        if not patient_name:
            frappe.throw(_("Patient not found"))

    appointments = frappe.get_all(
        "Appointment",
        filters={"patient": patient_name, "docstatus": ["!=", 2]},
        fields=[
            "name", "doctor", "appointment_date", "appointment_time",
            "status", "reason", "symptoms", "referral_type", "fast_track",
            "ai_priority", "queue_token", "visit_stage", "checked_in",
            "created_at",
        ],
        order_by="appointment_date desc, appointment_time desc",
    )

    for a in appointments:
        if a.doctor:
            dname = frappe.db.get_value("Doctor Profile", a.doctor, "full_name")
            a.doctor_name = dname

    patient_doc = frappe.db.get_value(
        "Patient Profile", patient_name,
        ["full_name", "phone", "age", "gender"], as_dict=True
    )

    return {
        "success": True,
        "patient": patient_name,
        "patient_details": patient_doc or {},
        "appointments": appointments,
        "message": _("Patient history loaded"),
    }


# ---------------------------------------------------------------------------
# Report Upload with Production-Grade Validations
# ---------------------------------------------------------------------------

ALLOWED_REPORT_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
MAX_REPORT_SIZE_MB = 10
MAX_REPORT_SIZE_BYTES = MAX_REPORT_SIZE_MB * 1024 * 1024


def _validate_report_file(file_data: bytes, file_name: str) -> str:
    """Validate uploaded report file. Returns the detected extension (lowercased)."""
    import os as _os

    if not file_data:
        frappe.throw(_("No file data provided"))
    if not file_name:
        frappe.throw(_("File name is required"))

    ext = _os.path.splitext(file_name)[1].lower()
    if ext not in ALLOWED_REPORT_EXTENSIONS:
        frappe.throw(
            _("Unsupported file type '{0}'. Allowed: {1}").format(
                ext, ", ".join(sorted(ALLOWED_REPORT_EXTENSIONS))
            )
        )

    if len(file_data) > MAX_REPORT_SIZE_BYTES:
        frappe.throw(
            _("File too large ({0:.1f} MB). Maximum allowed: {1} MB").format(
                len(file_data) / (1024 * 1024), MAX_REPORT_SIZE_MB
            )
        )

    return ext


@frappe.whitelist()
def upload_report(
    file_data=None,
    file_name=None,
    patient=None,
    appointment=None,
    title=None,
    report_type="Document",
    description=None,
):
    """
    Upload a medical report (image or PDF) with production-grade validations.

    Parameters:
        file_data: base64-encoded file content
        file_name: original file name
        patient: Patient Profile name or user email
        appointment: linked Appointment name (optional)
        title: report title (required)
        report_type: Lab | Imaging | Prescription | Document | Other
        description: optional description/instructions
    """
    require_login()

    if not title or not str(title).strip():
        frappe.throw(_("Report title is required"))

    if report_type not in ("Lab", "Imaging", "Prescription", "Document", "Other"):
        frappe.throw(_("Invalid report type"))

    # Resolve patient
    patient_name = _resolve_patient(patient) if patient else current_patient()
    if not patient_name:
        frappe.throw(_("Patient not found"))

    # Validate appointment if provided
    if appointment:
        appt_exists = frappe.db.exists("Appointment", appointment)
        if not appt_exists:
            frappe.throw(_("Appointment '{0}' not found").format(appointment))

    # Decode and validate file
    import base64 as _b64

    if not file_data:
        frappe.throw(_("No file uploaded"))

    try:
        file_bytes = _b64.b64decode(file_data, validate=True)
    except Exception:
        frappe.throw(_("Invalid file data (not valid base64)"))

    ext = _validate_report_file(file_bytes, file_name or "report")

    # Save file via Frappe File doctype
    file_doc = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": (file_name or "report") + ext,
            "content": file_bytes,
            "is_private": 0,
        }
    )
    file_doc.save(ignore_permissions=True)
    frappe.db.commit()

    # Create Patient Report record
    report_doc = frappe.get_doc(
        {
            "doctype": "Patient Report",
            "patient": patient_name,
            "appointment": appointment or None,
            "report_type": report_type,
            "title": title.strip(),
            "description": description or "",
            "report_file": file_doc.file_url,
            "uploaded_by": frappe.session.user,
            "uploaded_at": frappe.utils.now_datetime(),
            "status": "Uploaded",
        }
    )
    report_doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "success": True,
        "report_name": report_doc.name,
        "file_url": file_doc.file_url,
        "file_name": file_doc.file_name,
        "file_size": len(file_bytes),
        "extension": ext,
        "message": _("Report uploaded successfully"),
    }


@frappe.whitelist()
def preview_report(file_url=None, file_name=None):
    """
    Return file info for preview. The actual file is served by Frappe's
    /files/ URL which handles inline viewing for images and PDFs.
    """
    require_login()
    if not file_url:
        frappe.throw(_("File URL is required"))
    return {
        "file_url": file_url,
        "file_name": file_name or file_url.split("/")[-1],
        "can_preview": True,
    }


@frappe.whitelist()
def list_patient_reports(patient=None):
    """
    List medical reports for a patient.
    """
    require_login()

    patient_name = _resolve_patient(patient) if patient else current_patient()
    if not patient_name:
        frappe.throw(_("Patient not found"))

    reports = frappe.get_all(
        "Patient Report",
        filters={"patient": patient_name},
        fields=[
            "name", "patient", "appointment", "referral", "ordered_by",
            "report_type", "title", "laboratory", "external", "status",
            "sample_collected_at", "description", "findings",
            "report_file", "uploaded_by", "uploaded_at", "reviewed_by",
            "reviewed_at", "creation", "modified",
        ],
        order_by="creation desc",
    )

    return {
        "success": True,
        "patient": patient_name,
        "reports": reports,
        "message": _("Reports loaded"),
    }