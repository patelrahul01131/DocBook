"""
DocBook Review API.

Wires up the previously-orphaned ``Review`` doctype so patients can review a
completed appointment and the doctor's average ``Doctor Profile.rating`` stays
in sync. Powers the "Write Review" flow in My Appointments and the reviews
section on a doctor's public profile.
"""

import frappe
from frappe import _


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_auth():
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in first"), frappe.AuthenticationError)


def _get_patient_profile(user=None):
	"""Return the Patient Profile dict (name, full_name, user) for a user."""
	user = user or frappe.session.user
	return frappe.db.get_value(
		"Patient Profile",
		{"user": user},
		["name", "full_name", "user"],
		as_dict=True,
	)


def _resolve_appointment(appointment_id):
	"""Fetch an Appointment by name or slot and return it as a dict."""
	if not appointment_id:
		frappe.throw(_("Appointment ID is required"))

	appt = frappe.db.get_value(
		"Appointment",
		{"name": appointment_id},
		[
			"name",
			"patient",
			"doctor",
			"appointment_date",
			"appointment_time",
			"status",
		],
		as_dict=True,
	)
	if appt:
		return appt

	# Fallback: match by slot reference.
	return frappe.db.get_value(
		"Appointment",
		{"slot": appointment_id},
		[
			"name",
			"patient",
			"doctor",
			"appointment_date",
			"appointment_time",
			"status",
		],
		as_dict=True,
	)


def _recompute_doctor_rating(doctor):
	"""Average all reviews for a doctor and store onto Doctor Profile.rating."""
	rows = frappe.get_all(
		"Review",
		filters={"doctor": doctor},
		pluck="rating",
	)
	average = round(sum(rows) / len(rows), 2) if rows else 5.0
	frappe.db.set_value("Doctor Profile", doctor, "rating", average)
	return average


# ---------------------------------------------------------------------------
# Public APIs
# ---------------------------------------------------------------------------

@frappe.whitelist()
def submit_review(appointment_id, rating, feedback=None):
	"""
	Submit a patient review for a completed appointment.

	- Only the patient who owns the appointment may review it.
	- The appointment must be Completed.
	- One review per appointment.
	Recomputes the doctor's average rating on success.
	"""
	_require_auth()

	rating = int(rating or 0)
	if rating < 1 or rating > 5:
		frappe.throw(_("Rating must be between 1 and 5"))

	appt = _resolve_appointment(appointment_id)
	if not appt:
		frappe.throw(
			_("Appointment '{0}' not found").format(appointment_id),
			frappe.DoesNotExistError,
		)

	# Authorization: only the owning patient can review.
	patient = _get_patient_profile()
	if not patient or appt.patient != patient.name:
		frappe.throw(
			_("You can only review your own appointments"),
			frappe.PermissionError,
		)

	if appt.status != "Completed":
		frappe.throw(_("You can only review a completed appointment"))

	if frappe.db.exists("Review", {"appointment": appt.name}):
		frappe.throw(_("This appointment has already been reviewed"))

	review = frappe.get_doc(
		{
			"doctype": "Review",
			"appointment": appt.name,
			"doctor": appt.doctor,
			"patient": patient.name,
			"rating": rating,
			"feedback": (feedback or "").strip(),
			"review_date": frappe.utils.now_datetime(),
		}
	)
	review.insert(ignore_permissions=True)

	average = _recompute_doctor_rating(appt.doctor)
	frappe.db.commit()

	return {
		"success": True,
		"name": review.name,
		"rating": rating,
		"doctor_rating": average,
		"message": _("Thank you for your review"),
	}


@frappe.whitelist(allow_guest=True)
def get_doctor_reviews(doctor, limit=20):
	"""
	Return recent reviews for a doctor (accepts Doctor Profile name or User email).

	Also returns aggregate rating stats used by the public doctor profile.
	"""
	if not doctor:
		frappe.throw(_("Doctor is required"))

	doctor_name = doctor
	if not frappe.db.exists("Doctor Profile", doctor_name):
		by_user = frappe.db.get_value("Doctor Profile", {"user": doctor_name}, "name")
		if by_user:
			doctor_name = by_user
		else:
			frappe.throw(
				_("Doctor profile not found for '{0}'").format(doctor),
				frappe.DoesNotExistError,
			)

	limit = max(1, min(int(limit or 20), 100))

	reviews = frappe.get_all(
		"Review",
		filters={"doctor": doctor_name},
		fields=[
			"name",
			"rating",
			"feedback",
			"review_date",
			"patient",
		],
		order_by="review_date DESC",
		limit=limit,
	)

	# Attach patient display names without leaking user emails.
	patient_names = {r.patient for r in reviews if r.patient}
	names = {}
	if patient_names:
		for row in frappe.get_all(
			"Patient Profile",
			filters={"name": ["in", list(patient_names)]},
			fields=["name", "full_name"],
		):
			names[row.name] = row.full_name or row.name

	for r in reviews:
		r.patient_name = names.get(r.patient, "A patient")

	stats = frappe.get_all(
		"Review",
		filters={"doctor": doctor_name},
		fields=["AVG(rating) AS average", "COUNT(name) AS total"],
	)[0]

	return {
		"doctor": doctor_name,
		"average": round(stats.average or 0, 2),
		"total": int(stats.total or 0),
		"reviews": reviews,
	}


@frappe.whitelist()
def get_review_for_appointment(appointment_id):
	"""
	Return the review for a given appointment if one exists, else None.

	Lets the UI decide between "Write Review" and "View Review".
	"""
	_require_auth()

	name = frappe.db.get_value("Review", {"appointment": appointment_id}, "name")
	if not name:
		return None

	return frappe.db.get_value(
		"Review",
		name,
		["name", "rating", "feedback", "review_date"],
		as_dict=True,
	)


@frappe.whitelist()
def get_my_reviews():
	"""
	Return a map of appointment name -> review for the authenticated patient.

	Lets the My Appointments list show "Reviewed" vs "Write Review" in bulk.
	"""
	_require_auth()

	patient = _get_patient_profile()
	if not patient:
		return {}

	rows = frappe.get_all(
		"Review",
		filters={"patient": patient.name},
		fields=["name", "appointment", "rating", "feedback", "review_date"],
	)

	return {r.appointment: r for r in rows}