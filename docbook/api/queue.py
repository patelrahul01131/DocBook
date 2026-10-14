"""
DocBook Queue Management API
Receptionist-driven check-in, token assignment, and call-next. The ordering
puts 'Ready For Review' return visits ahead of newly waiting patients so a
patient returning with a completed report is called next without re-queueing.
"""

import secrets

import frappe
from frappe import _

from docbook.api.access import (
	require_login, is_admin, is_receptionist, current_doctor, current_patient,
)
from docbook.api.appointment import validate_appointment_booking, _get_doctor_name

QUEUE_ACTIVE_STAGES = ("Waiting", "In Consultation", "Ready For Review")


def _stage_rank(stage):
	# In Consultation = now serving (0); Ready For Review = return visit (1);
	# Waiting = fresh arrival (2); everything else is inactive.
	if stage == "In Consultation":
		return 0
	if stage == "Ready For Review":
		return 1
	if stage == "Waiting":
		return 2
	return 3


def _resolve_doctor(doctor=None):
	if doctor:
		return frappe.db.get_value("Doctor Profile", {"user": doctor}, "name") \
			or (doctor if frappe.db.exists("Doctor Profile", doctor) else None)
	return current_doctor()


def _is_queue_actor(doctor_name=None):
	"""Receptionists/admins manage any queue; doctors manage their own."""
	if is_admin() or is_receptionist():
		return True
	return bool(current_doctor())


def _queue_rows(doctor, date):
	"""Fetch and rank today's queue for a doctor (or all if doctor is None)."""
	filters = {"appointment_date": date, "status": ["in", ["Pending", "Confirmed"]]}
	if doctor:
		filters["doctor"] = doctor

	rows = frappe.get_all(
		"Appointment",
		filters=filters,
		fields=["name", "patient", "doctor", "appointment_time", "status", "reason",
			"visit_stage", "queue_token", "priority", "checked_in", "checked_in_at",
			"called_at", "referral"],
		order_by="appointment_time asc",
	)

	# Patient + doctor display names.
	patients = {r.patient for r in rows}
	if patients:
		for p in frappe.get_all("Patient Profile",
			filters={"name": ["in", list(patients)]}, fields=["name", "full_name"]):
			for r in rows:
				if r.patient == p.name:
					r.patient_name = p.full_name
	doctors = {r.doctor for r in rows}
	if doctors:
		for d in frappe.get_all("Doctor Profile",
			filters={"name": ["in", list(doctors)]}, fields=["name", "full_name"]):
			for r in rows:
				if r.doctor == d.name:
					r.doctor_name = d.full_name

	for r in rows:
		r.stage_rank = _stage_rank(r.visit_stage)
		r.active = 1 if (r.checked_in and r.visit_stage in QUEUE_ACTIVE_STAGES) else 0

	active = [r for r in rows if r["active"]]
	active.sort(key=lambda r: (r.stage_rank, r.queue_token or 10 ** 6,
		str(r.appointment_time or "")))
	for i, r in enumerate(active, start=1):
		r.queue_position = i

	inactive = [r for r in rows if not r["active"]]
	return active, inactive


def _next_token(doctor, date):
	"""Next daily queue token for a doctor on a date (shared by check-in & walk-ins)."""
	last = frappe.db.sql(
		"""SELECT MAX(queue_token) FROM `tabAppointment`
		   WHERE doctor = %(doc)s AND appointment_date = %(date)s""",
		{"doc": doctor, "date": date},
	)[0][0] or 0
	return last + 1


@frappe.whitelist()
def get_queue(doctor=None, date=None):
	"""Return the ranked queue for a doctor (or all doctors) on a date."""
	require_login()
	date = frappe.utils.getdate(date) if date else frappe.utils.getdate()

	doctor_name = _resolve_doctor(doctor)
	# A doctor without an explicit target sees their own queue; receptionists
	# without a target see all doctors.
	if doctor and not doctor_name:
		frappe.throw(_("Doctor not found"), frappe.DoesNotExistError)
	if not doctor and not doctor_name and not (is_receptionist() or is_admin()):
		frappe.throw(_("Not authorized to view the queue"), frappe.PermissionError)

	active, inactive = _queue_rows(doctor_name, date)

	now_serving = next((r for r in active if r.visit_stage == "In Consultation"), None)
	return {
		"date": str(date),
		"doctor": doctor_name,
		"now_serving": now_serving,
		"queue": active,
		"other": inactive,
		"waiting_count": sum(1 for r in active if r.visit_stage in ("Waiting", "Ready For Review")),
	}


@frappe.whitelist()
def check_in_patient(appointment):
	"""Receptionist checks a patient in, assigns a token, and places them in
	the queue. Return-visits (priority) keep their 'Ready For Review' stage so
	they sort ahead of new arrivals."""
	require_login()
	if not _is_queue_actor():
		frappe.throw(_("Not authorized to manage the queue"), frappe.PermissionError)

	appt = frappe.db.get_value(
		"Appointment", appointment,
		["name", "patient", "doctor", "appointment_date", "status", "visit_stage",
		 "queue_token", "priority", "checked_in"], as_dict=True)
	if not appt:
		frappe.throw(_("Appointment not found"), frappe.DoesNotExistError)
	if appt.status in ("Completed", "Cancelled"):
		frappe.throw(_("Cannot check in a {0} appointment").format(appt.status))

	# Assign a daily token for this doctor if the patient hasn't one.
	token = appt.queue_token or _next_token(appt.doctor, appt.appointment_date)

	stage = appt.visit_stage
	if not stage or stage not in QUEUE_ACTIVE_STAGES:
		stage = "Waiting"
	# A priority/return visit keeps "Ready For Review"; a fresh one waits.
	if appt.priority and appt.visit_stage == "Ready For Review":
		stage = "Ready For Review"

	frappe.db.set_value("Appointment", appointment, {
		"checked_in": 1,
		"checked_in_at": frappe.utils.now_datetime(),
		"queue_token": token,
		"visit_stage": stage,
	})
	frappe.db.commit()

	active, inactive = _queue_rows(appt.doctor, appt.appointment_date)
	pos = next((r.queue_position for r in active if r.name == appointment), None)
	return {"success": True, "token": token, "queue_position": pos, "visit_stage": stage}


@frappe.whitelist()
def call_next_patient(doctor=None, date=None):
	"""Call the next patient in the queue. 'Ready For Review' return visits
	are called before newly waiting patients, so report-returners skip the wait.
	Returns the appointment now in consultation."""
	require_login()
	if not _is_queue_actor():
		frappe.throw(_("Not authorized to manage the queue"), frappe.PermissionError)

	doctor_name = _resolve_doctor(doctor) or current_doctor()
	if not doctor_name:
		frappe.throw(_("Doctor is required"), frappe.ValidationError)

	# Live calling happens on a concrete day (today by default); the desk can
	# preview past/future days, but tokens belong to the viewed date only.
	qdate = frappe.utils.getdate(date) if date else frappe.utils.getdate()

	# Ensure nobody is left stranded in 'In Consultation'.
	active, inactive = _queue_rows(doctor_name, qdate)
	current = next((r for r in active if r.visit_stage == "In Consultation"), None)

	# Next candidate: waiting or ready-for-review, ranked (return visits first).
	candidates = [r for r in active
		if r.visit_stage in ("Waiting", "Ready For Review")]
	if not candidates:
		return {"success": False, "message": _("No patients waiting"), "now_serving": current}

	candidates.sort(key=lambda r: (r.stage_rank, r.queue_token or 10 ** 6,
		str(r.appointment_time or "")))
	nxt = candidates[0]

	frappe.db.set_value("Appointment", nxt.name, {
		"visit_stage": "In Consultation",
		"called_at": frappe.utils.now_datetime(),
		"checked_in": 1,
	})
	frappe.db.commit()

	active, inactive = _queue_rows(doctor_name, qdate)
	now_serving = next((r for r in active if r.visit_stage == "In Consultation"), None)
	return {"success": True, "now_serving": now_serving,
		"called": nxt.name, "queue": active}


@frappe.whitelist()
def mark_visit_completed(appointment):
	"""Complete an appointment and free its queue slot."""
	require_login()
	appt = frappe.db.get_value(
		"Appointment", appointment, ["name", "doctor", "status"], as_dict=True)
	if not appt:
		frappe.throw(_("Appointment not found"), frappe.DoesNotExistError)

	if not (is_admin() or is_receptionist()
		or current_doctor() == appt.doctor):
		frappe.throw(_("Not authorized"), frappe.PermissionError)

	frappe.db.set_value("Appointment", appointment, {
		"status": "Completed", "visit_stage": "Completed"})
	frappe.db.commit()
	return {"success": True, "status": "Completed"}


@frappe.whitelist()
def get_my_queue_position(appointment=None):
	"""Patient-facing: their position in today's queue."""
	require_login()
	patient = current_patient()
	if not patient:
		frappe.throw(_("Patient profile not found"), frappe.PermissionError)

	today = frappe.utils.getdate()
	if appointment:
		filters = {"name": appointment, "patient": patient}
	else:
		filters = {"patient": patient, "appointment_date": today,
			"status": ["in", ["Pending", "Confirmed"]]}

	appt = frappe.db.get_value("Appointment", filters,
		["name", "doctor", "appointment_date", "visit_stage", "queue_token",
		 "checked_in", "priority"], as_dict=True)
	if not appt:
		return {"found": False}

	active, inactive = _queue_rows(appt.doctor, appt.appointment_date)
	pos = next((r.queue_position for r in active if r.name == appt.name), None)
	return {
		"found": True,
		"appointment": appt.name,
		"queue_position": pos,
		"queue_token": appt.queue_token,
		"visit_stage": appt.visit_stage,
		"checked_in": appt.checked_in,
		"priority": appt.priority,
	}


# ---------------------------------------------------------------------------
# Receptionist: patient lookup, walk-in booking, and day-of rescheduling
# ---------------------------------------------------------------------------

def _require_reception():
	"""Only receptionists and admins may run at-desk reception actions."""
	require_login()
	if not (is_admin() or is_receptionist()):
		frappe.throw(_("Not authorized to manage the queue"), frappe.PermissionError)


def _norm_email(email):
	return (email or "").strip().lower() or None


DEFAULT_COUNTRY_CODE = "+91"


def _canon_phone(phone):
	"""Canonical digit form for matching: drop trunk/country prefixes, keep last 10."""
	d = "".join(c for c in (phone or "") if c.isdigit())
	if not d:
		return ""
	d = d.lstrip("0") or d
	return d[-10:] if len(d) >= 10 else d


def _storage_phone(phone):
	"""International format the Phone field accepts (it requires a country code)."""
	raw = (phone or "").strip()
	if not raw:
		return ""
	if raw.startswith("+"):
		return raw
	d = "".join(c for c in raw if c.isdigit()).lstrip("0")
	if not d:
		return ""
	if len(d) == 10:
		return DEFAULT_COUNTRY_CODE + d          # plain national number -> default CC
	if len(d) == 12 and d.startswith("91"):
		return "+" + d
	return "+" + d


def _norm_phone(phone):
	raw = (phone or "").strip()
	return raw or None, _canon_phone(phone)


def _gen_password():
	"""Frappe-valid password: upper, lower, digit, symbol, length >= 12."""
	lower = "abcdefghijkmnpqrstuvwxyz"
	return (
		secrets.choice(lower.upper())
		+ secrets.choice(lower)
		+ secrets.choice("23456789")
		+ secrets.choice("!@#$%^&*")
		+ "".join(secrets.choice(lower + "23456789") for _ in range(10))
	)


def _find_by_phone(phone_raw):
	"""Match a phone number against Patient Profile.phone regardless of country/trunk prefix."""
	target = _canon_phone(phone_raw)
	if not target:
		return None
	rows = frappe.get_all(
		"Patient Profile", filters=[["phone", "is", "set"]],
		fields=["name", "phone"], limit=1000)
	for r in rows:
		if _canon_phone(r.phone) == target:
			return r.name
	return None


@frappe.whitelist()
def lookup_patient(email=None, phone=None):
	"""Find an existing patient by email or phone so walk-ins don't create duplicates."""
	_require_reception()
	email = _norm_email(email)
	phone_raw, _canon_looked_up = _norm_phone(phone)

	patient = None
	if email:
		patient = frappe.db.exists("Patient Profile", email) \
			or frappe.db.get_value("Patient Profile", {"user": email}, "name")
	if not patient:
		patient = _find_by_phone(phone_raw)

	if not patient:
		return {"found": False}

	doc = frappe.db.get_value(
		"Patient Profile", patient,
		["name", "full_name", "phone", "user", "age", "gender"], as_dict=True)
	return {
		"found": True, "patient": doc.name, "full_name": doc.full_name,
		"email": doc.user, "phone": doc.phone, "age": doc.age, "gender": doc.gender,
	}


def _resolve_or_create_patient(full_name=None, email=None, phone=None,
	age=None, gender=None, patient=None):
	"""Return ``(patient_profile_name, user_created)``.

	Resolution order: explicit profile -> existing email -> existing phone. Only when no
	match is found do we create a brand new ``User`` (Patient role) + ``Patient Profile``,
	which requires a name and an email for the login.
	"""
	email = _norm_email(email)
	phone_raw, _canon_resolve = _norm_phone(phone)
	full_name = (full_name or "").strip()

	# 1. Explicit profile
	if patient and frappe.db.exists("Patient Profile", patient):
		return patient, False

	# 2. Existing email
	if email:
		by_email = frappe.db.exists("Patient Profile", email) \
			or frappe.db.get_value("Patient Profile", {"user": email}, "name")
		if by_email:
			return by_email, False

	# 3. Existing phone (avoid duplicate accounts for returning walk-ins)
	if phone_raw:
		by_phone = _find_by_phone(phone_raw)
		if by_phone:
			return by_phone, False

	# 4. Create new — name + email are mandatory for a login-able account.
	if not full_name or not email:
		frappe.throw(_("Name and email are required to register a new patient"))

	user_created = False
	if frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)   # e.g. staff account already exists
	else:
		user = frappe.get_doc({
			"doctype": "User",
			"email": email,
			"first_name": full_name,
			"enabled": 1,
			"user_type": "Website User",
			"send_welcome_email": 0,
			"roles": [{"role": "Patient"}],
		})
		user.insert(ignore_permissions=True)
		user.new_password = _gen_password()
		user.save(ignore_permissions=True)
		user_created = True

	existing = frappe.db.exists("Patient Profile", email) \
		or frappe.db.get_value("Patient Profile", {"user": email}, "name")
	if existing:
		return existing, user_created

	full_name_val = full_name or (user.full_name or email.split("@")[0])
	age_val = None
	if age not in (None, "", 0):
		try:
			age_val = int(age)
		except (TypeError, ValueError):
			age_val = None

	# The Phone field requires an international number; if it still won't validate we
	# store the profile without a phone rather than block a walk-in booking.
	for attempt_phone in (_storage_phone(phone_raw), ""):
		profile = frappe.get_doc({
			"doctype": "Patient Profile",
			"user": email,
			"full_name": full_name_val,
			"phone": attempt_phone,
		})
		if age_val is not None:
			profile.age = age_val
		if gender:
			profile.gender = gender
		try:
			profile.insert(ignore_permissions=True)
			break
		except frappe.InvalidPhoneNumberError:
			continue
	else:
		frappe.throw(_("Could not save the patient's phone number"))

	return profile.name, user_created


@frappe.whitelist()
def create_walkin_appointment(doctor, appointment_date=None, appointment_time=None,
	full_name=None, email=None, phone=None, age=None, gender=None, patient=None,
	reason=None, symptoms=None):
	"""At-desk walk-in booking: create/resolve the patient (auto-creating a User account
	when they're new), book the slot, and drop them straight into the live queue."""
	_require_reception()

	doctor_name = _get_doctor_name(doctor)
	patient_name, user_created = _resolve_or_create_patient(
		full_name=full_name, email=email, phone=phone,
		age=age, gender=gender, patient=patient,
	)

	today = frappe.utils.getdate()
	apt_date = frappe.utils.getdate(appointment_date) if appointment_date else today

	if appointment_time:
		apt_time = frappe.utils.get_time(appointment_time)
	elif apt_date == today:
		apt_time = frappe.utils.nowtime()          # patient is standing here — book now
	else:
		frappe.throw(_("Please choose a time slot for a future walk-in booking"))

	# immediate=True allows the at-desk "now" slot; all other rules still apply.
	val = validate_appointment_booking(
		doctor=doctor_name,
		patient=patient_name,
		appointment_date=apt_date,
		appointment_time=apt_time,
		immediate=True,
	)

	slot = frappe.get_doc({
		"doctype": "Availability Slot",
		"doctor": val["doctor_name"],
		"date": val["appointment_date"],
		"start_time": val["appointment_time"],
		"end_time": val["end_time"],
		"is_booked": 1,
	})
	slot.insert(ignore_permissions=True)

	token = _next_token(val["doctor_name"], val["appointment_date"])
	appt = frappe.get_doc({
		"doctype": "Appointment",
		"patient": val["patient_name"],
		"doctor": val["doctor_name"],
		"slot": slot.name,
		"appointment_date": val["appointment_date"],
		"appointment_time": val["appointment_time"],
		"status": "Pending",
		"reason": (reason or "").strip(),
		"symptoms": (symptoms or "").strip(),
		"consultation_fee": val["consultation_fee"],
		"payment_status": "Pending",
		"created_at": frappe.utils.now_datetime(),
		"visit_stage": "Waiting",
		"queue_token": token,
		"checked_in": 1,
		"checked_in_at": frappe.utils.now_datetime(),
	})
	appt.insert(ignore_permissions=True)
	frappe.db.commit()

	active, _inactive_rows = _queue_rows(val["doctor_name"], val["appointment_date"])
	pos = next((r.queue_position for r in active if r.name == appt.name), None)
	return {
		"success": True,
		"message": _("Walk-in appointment booked and checked in"),
		"appointment": appt.name,
		"patient": val["patient_name"],
		"user_created": user_created,
		"email": _norm_email(email),
		"token": token,
		"queue_position": pos,
		"appointment_date": str(val["appointment_date"]),
		"appointment_time": str(val["appointment_time"])[:5],
	}


@frappe.whitelist()
def receptionist_reschedule(appointment, appointment_date, appointment_time, reason=None):
	"""Reschedule an appointment for a patient who arrived early, late, or on another day.

	Different day -> full queue reset (they re-check-in when they arrive). Same day -> keep
	their check-in so they hold their place, but re-queue for the new time.
	"""
	_require_reception()

	appt = frappe.db.get_value(
		"Appointment", appointment,
		["name", "patient", "doctor", "slot", "appointment_date", "appointment_time",
		 "status", "visit_stage", "checked_in", "queue_token"],
		as_dict=True,
	)
	if not appt:
		frappe.throw(_("Appointment not found"), frappe.DoesNotExistError)
	if appt.status in ("Completed", "Cancelled"):
		frappe.throw(_("Cannot reschedule a {0} appointment").format(appt.status))

	new_date = frappe.utils.getdate(appointment_date)
	# immediate=True lets a late/early patient be moved to right now on their day.
	val = validate_appointment_booking(
		doctor=appt.doctor,
		patient=appt.patient,
		appointment_date=new_date,
		appointment_time=frappe.utils.get_time(appointment_time),
		exclude_appointment=appt.name,
		immediate=True,
	)

	# Free the old slot and reserve the new one.
	if appt.slot and frappe.db.exists("Availability Slot", appt.slot):
		frappe.db.set_value("Availability Slot", appt.slot, "is_booked", 0)
	new_slot = frappe.get_doc({
		"doctype": "Availability Slot",
		"doctor": appt.doctor,
		"date": val["appointment_date"],
		"start_time": val["appointment_time"],
		"end_time": val["end_time"],
		"is_booked": 1,
	})
	new_slot.insert(ignore_permissions=True)

	same_day = str(val["appointment_date"]) == str(appt.appointment_date)
	updates = {
		"appointment_date": val["appointment_date"],
		"appointment_time": val["appointment_time"],
		"slot": new_slot.name,
	}
	if reason:
		updates["reason"] = reason

	if not same_day:
		# Moved to a different day: clear today's queue state entirely.
		updates.update({
			"checked_in": 0, "checked_in_at": None, "called_at": None,
			"queue_token": None, "visit_stage": "",
		})
	elif appt.checked_in:
		# Same day and already here: hold their place, re-queue for the new time.
		updates.update({
			"visit_stage": "Waiting",
			"queue_token": appt.queue_token or _next_token(appt.doctor, val["appointment_date"]),
			"called_at": None,
		})
	else:
		# Same day, not yet arrived: keep it a clean scheduled booking.
		updates.update({"queue_token": None, "called_at": None, "visit_stage": ""})

	frappe.db.set_value("Appointment", appt.name, updates)
	frappe.db.commit()

	active, _inactive_after_resched = _queue_rows(appt.doctor, val["appointment_date"])
	pos = next((r.queue_position for r in active if r.name == appt.name), None)
	return {
		"success": True,
		"message": _("Appointment rescheduled"),
		"appointment": appt.name,
		"appointment_date": str(val["appointment_date"]),
		"appointment_time": str(val["appointment_time"])[:5],
		"checked_in": updates.get("checked_in", appt.checked_in or 0),
		"queue_position": pos,
	}

