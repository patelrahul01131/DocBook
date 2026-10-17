"""
DocBook Referral API
Doctor-to-doctor referrals that group two appointments under one shared
care episode. Both doctors see the shared reports, prescriptions, notes.
"""

import frappe
from frappe import _

from docbook.api.appointment import create_appointment, _get_patient_name


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _current_doctor(user=None):
	"""Resolve the authenticated doctor's profile name, or None."""
	user = user or frappe.session.user
	if not user or user == "Guest":
		return None
	return frappe.db.get_value("Doctor Profile", {"user": user}, "name")


def _require_doctor():
	"""Throw unless the session user is a doctor (or System Manager)."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in first"), frappe.AuthenticationError)
	return _current_doctor()


def _is_admin():
	return "System Manager" in frappe.get_roles(frappe.session.user)


def _referral_or_throw(referral):
	ref = frappe.db.get_value(
		"Referral",
		referral,
		["name", "patient", "referring_doctor", "referred_to_doctor", "source_appointment",
		 "target_appointment", "status", "reason", "clinical_notes", "specialty", "referral_date"],
		as_dict=True,
	)
	if not ref:
		frappe.throw(_("Referral '{0}' not found").format(referral), frappe.DoesNotExistError)
	return ref


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@frappe.whitelist()
def create_referral(
	source_appointment,
	referred_to_doctor,
	reason,
	clinical_notes=None,
	appointment_date=None,
	appointment_time=None,
):
	"""
	Create a referral from the referring doctor's current appointment to a
	referred specialist. Optionally book the specialist appointment immediately
	when a date/time is supplied.
	"""
	doctor = _require_doctor()
	if not doctor and not _is_admin():
		frappe.throw(_("Only doctors can create referrals"), frappe.PermissionError)

	src = frappe.db.get_value(
		"Appointment",
		source_appointment,
		["name", "patient", "doctor", "referral", "status"],
		as_dict=True,
	)
	if not src:
		frappe.throw(_("Source appointment '{0}' not found").format(source_appointment),
			frappe.DoesNotExistError)

	# Authorization: caller must own the source appointment (or be admin).
	if not _is_admin() and src.doctor != doctor:
		frappe.throw(_("You are not authorized to refer from this appointment"),
			frappe.PermissionError)

	if src.referral:
		frappe.throw(_("This appointment already belongs to referral {0}").format(src.referral))

	if not reason or not str(reason).strip():
		frappe.throw(_("A reason for referral is required"))

	referred_name = frappe.db.get_value("Doctor Profile", {"user": referred_to_doctor}, "name") \
		or (referred_to_doctor if frappe.db.exists("Doctor Profile", referred_to_doctor) else None)
	if not referred_name:
		frappe.throw(_("Referred doctor not found"))
	if referred_name == src.doctor:
		frappe.throw(_("Cannot refer to the same doctor"))

	specialty = frappe.db.get_value("Doctor Profile", referred_name, "specialty")

	# Optionally book the specialist appointment now.
	target_appointment = None
	if appointment_date and appointment_time:
		res = create_appointment(
			patient=src.patient,
			doctor=referred_name,
			appointment_date=appointment_date,
			appointment_time=appointment_time,
			reason="Referral: {0}".format(reason),
			symptoms=clinical_notes or "",
		)
		target_appointment = res.get("name")

	ref = frappe.get_doc({
		"doctype": "Referral",
		"patient": src.patient,
		"referring_doctor": src.doctor,
		"referred_to_doctor": referred_name,
		"specialty": specialty,
		"source_appointment": source_appointment,
		"target_appointment": target_appointment,
		"status": "Pending",
		"reason": reason,
		"clinical_notes": clinical_notes or "",
		"referral_date": frappe.utils.now_datetime(),
	})
	ref.insert(ignore_permissions=True)
	frappe.db.commit()

	# on_update links both appointments; ensure source is linked even if
	# target wasn't booked yet.
	frappe.db.set_value("Appointment", source_appointment, "referral", ref.name)

	# Notify the referred doctor (best-effort).
	try:
		referred_user = frappe.db.get_value("Doctor Profile", referred_name, "user")
		if referred_user and referred_user != "Guest":
			frappe.sendmail(
				recipients=[referred_user],
				subject=_("New referral: {0}").format(ref.name),
				message=_("You have received a referral for patient {0}. Reason: {1}").format(
					src.patient, reason),
			)
	except Exception:
		frappe.log_error(title="Referral notification failed", message=frappe.get_traceback())

	return {"success": True, "referral": ref.name, "target_appointment": target_appointment}


@frappe.whitelist()
def link_appointment_to_referral(appointment, referral):
	"""Attach a later-booked appointment to an existing referral episode."""
	ref = _referral_or_throw(referral)
	appt = frappe.db.get_value("Appointment", appointment, ["name", "patient", "doctor"], as_dict=True)
	if not appt:
		frappe.throw(_("Appointment not found"), frappe.DoesNotExistError)
	if appt.patient != ref.patient:
		frappe.throw(_("Appointment does not belong to this referral's patient"))

	doctor = _current_doctor()
	if not _is_admin() and doctor not in (ref.referring_doctor, ref.referred_to_doctor):
		frappe.throw(_("Not authorized to modify this referral"), frappe.PermissionError)

	frappe.db.set_value("Appointment", appointment, "referral", referral)
	if not ref.target_appointment:
		frappe.db.set_value("Referral", referral, "target_appointment", appointment)
	frappe.db.commit()
	return {"success": True, "referral": referral}


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

@frappe.whitelist()
def list_my_referrals():
	"""All referrals where the current doctor is referring or referred."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in first"), frappe.AuthenticationError)

	doctor = _current_doctor()
	if not doctor and not _is_admin():
		return []

	if doctor:
		or_filters = [["referring_doctor", "=", doctor], ["referred_to_doctor", "=", doctor]]
		rows = frappe.get_all(
			"Referral",
			or_filters=or_filters,
			fields=["name", "patient", "referring_doctor", "referred_to_doctor", "specialty",
				"source_appointment", "target_appointment", "status", "reason", "referral_date"],
			order_by="referral_date desc",
		)
	else:
		rows = frappe.get_all(
			"Referral",
			fields=["name", "patient", "referring_doctor", "referred_to_doctor", "specialty",
				"source_appointment", "target_appointment", "status", "reason", "referral_date"],
			order_by="referral_date desc",
		)

	patients = {r.patient for r in rows}
	patient_names = {}
	if patients:
		for p in frappe.get_all("Patient Profile",
			filters={"name": ["in", list(patients)]}, fields=["name", "full_name"]):
			patient_names[p.name] = p.full_name

	for r in rows:
		r.patient_name = patient_names.get(r.patient)
		r.role = "Referring" if r.referring_doctor == doctor else (
			"Referred" if r.referred_to_doctor == doctor else "")
		r.report_count = frappe.db.count("Patient Report", {"referral": r.name})

	return rows


@frappe.whitelist()
def get_referral(referral):
	"""Full referral detail: both appointments, reports, prescriptions."""
	ref = _referral_or_throw(referral)

	doctor = _current_doctor()
	if not _is_admin() and doctor not in (ref.referring_doctor, ref.referred_to_doctor):
		try:
			patient = _get_patient_name()
		except Exception:
			patient = None
		if patient != ref.patient:
			frappe.throw(_("Not authorized to view this referral"), frappe.PermissionError)

	def _appt(name):
		if not name:
			return None
		return frappe.get_doc("Appointment", name)

	appointments = [a for a in (_appt(ref.source_appointment), _appt(ref.target_appointment)) if a]

	or_f = [["referral", "=", ref.name]]
	appt_names = [a.name for a in appointments]
	if appt_names:
		or_f.append(["appointment", "in", appt_names])
	reports = frappe.get_all(
		"Patient Report",
		or_filters=or_f,
		fields=["name", "appointment", "report_type", "title", "laboratory", "external",
			"status", "report_file", "findings", "uploaded_by", "uploaded_at", "ordered_by"],
		order_by="creation desc",
	)

	return {
		**ref,
		"appointments": [a.as_dict() for a in appointments],
		"reports": reports,
	}


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

@frappe.whitelist()
def accept_referral(referral):
	ref = _referral_or_throw(referral)
	doctor = _current_doctor()
	if not _is_admin() and doctor != ref.referred_to_doctor:
		frappe.throw(_("Only the referred doctor can accept this referral"),
			frappe.PermissionError)
	if ref.status != "Pending":
		frappe.throw(_("Only pending referrals can be accepted"))
	frappe.db.set_value("Referral", referral, {
		"status": "Accepted", "accepted_at": frappe.utils.now_datetime()})
	frappe.db.commit()
	return {"success": True, "status": "Accepted"}


@frappe.whitelist()
def reject_referral(referral, note=None):
	ref = _referral_or_throw(referral)
	doctor = _current_doctor()
	if not _is_admin() and doctor != ref.referred_to_doctor:
		frappe.throw(_("Only the referred doctor can reject this referral"),
			frappe.PermissionError)
	if ref.status != "Pending":
		frappe.throw(_("Only pending referrals can be rejected"))
	frappe.db.set_value("Referral", referral, "status", "Rejected")
	frappe.db.commit()
	return {"success": True, "status": "Rejected"}


@frappe.whitelist()
def complete_referral(referral):
	ref = _referral_or_throw(referral)
	doctor = _current_doctor()
	if not _is_admin() and doctor not in (ref.referring_doctor, ref.referred_to_doctor):
		frappe.throw(_("Not authorized to complete this referral"), frappe.PermissionError)
	frappe.db.set_value("Referral", referral, {
		"status": "Completed", "completed_at": frappe.utils.now_datetime()})
	frappe.db.commit()
	return {"success": True, "status": "Completed"}


@frappe.whitelist()
def update_referral(referral, reason=None, clinical_notes=None):
	"""Doctor or admin updates an existing referral."""
	ref = _referral_or_throw(referral)
	doctor = _current_doctor()
	if not _is_admin() and doctor != ref.referring_doctor:
		frappe.throw(_("Only the referring doctor can modify this referral"), frappe.PermissionError)

	updates = {}
	if reason is not None:
		if not str(reason).strip():
			frappe.throw(_("Reason cannot be empty"))
		updates["reason"] = str(reason).strip()
	if clinical_notes is not None:
		updates["clinical_notes"] = str(clinical_notes).strip()

	if updates:
		frappe.db.set_value("Referral", referral, updates)
		frappe.db.commit()

	return {"success": True, "referral": referral}


@frappe.whitelist()
def cancel_referral(referral):
	"""Doctor or admin cancels or deletes a referral and unlinks appointments."""
	ref = _referral_or_throw(referral)
	doctor = _current_doctor()
	if not _is_admin() and doctor != ref.referring_doctor:
		frappe.throw(_("Only the referring doctor can cancel this referral"), frappe.PermissionError)

	# Unlink source appointment
	if ref.source_appointment and frappe.db.exists("Appointment", ref.source_appointment):
		frappe.db.set_value("Appointment", ref.source_appointment, "referral", None)

	# If target appointment is still pending, cancel or delete it
	if ref.target_appointment and frappe.db.exists("Appointment", ref.target_appointment):
		target_status = frappe.db.get_value("Appointment", ref.target_appointment, "status")
		if target_status in ("Pending", "Confirmed"):
			frappe.db.set_value("Appointment", ref.target_appointment, "status", "Cancelled")

	frappe.delete_doc("Referral", referral, ignore_permissions=True)
	frappe.db.commit()
	return {"success": True, "referral": referral}


