import frappe
from frappe import _


def _get_doctor_profile(user=None):
	"""Resolve a doctor's profile by user, or None."""
	user = user or frappe.session.user
	if not user or user == "Guest":
		return None
	return frappe.db.get_value(
		"Doctor Profile",
		{"user": user},
		[
			"name", "user", "full_name", "phone", "specialty",
			"qualification", "experience_years", "consultation_fee",
			"bio", "profile_image", "is_approved", "rating"
		],
		as_dict=True,
	)


@frappe.whitelist(allow_guest=True)
def list_doctors():
	doctor = frappe.get_all(
		"Doctor Profile",
		fields=[
			"user",
			"full_name",
			"phone",
			"specialty",
			"qualification",
			"experience_years",
			"consultation_fee",
			"bio",
			"profile_image",
			"rating"
		]
	)
	return doctor


@frappe.whitelist(allow_guest=True)
def get_doctor_by_user(user_name):
	if not user_name:
		return None
	user_doc = frappe.get_doc("User", user_name)
	return frappe.get_doc("Doctor Profile", user_doc.name)


@frappe.whitelist(allow_guest=True)
def get_doctors_by_specialty(specialty=None):
	"""
	Return approved doctors for a given specialty.
	Used by the AI booking flow: patient describes a problem,
	AI identifies the specialty, then we list matching doctors.
	"""
	if not specialty:
		return []

	doctors = frappe.get_all(
		"Doctor Profile",
		filters={
			"specialty": specialty,
			"is_approved": 1,
		},
		fields=[
			"user",
			"full_name",
			"phone",
			"specialty",
			"qualification",
			"experience_years",
			"consultation_fee",
			"bio",
			"profile_image",
			"rating",
		],
		order_by="rating desc, full_name asc",
	)
	return doctors or []


@frappe.whitelist()
def get_doctor_dashboard():
	"""
	Return an aggregated payload for the doctor dashboard.

	Includes the doctor profile, today's schedule, key statistics, the
	next upcoming appointments, and the most recently seen patients.
	"""
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in first"), frappe.AuthenticationError)

	doctor = _get_doctor_profile()
	if not doctor:
		frappe.throw(_("Doctor profile not found for this account"))

	today = frappe.utils.getdate()
	today_str = today.strftime("%Y-%m-%d")
	now = frappe.utils.now_datetime()

	# All appointments for this doctor (needed for stats + lists).
	appointments = frappe.db.sql(
		"""
		SELECT
			a.name,
			a.patient,
			a.appointment_date,
			a.appointment_time,
			a.status,
			a.reason,
			a.diagnosis,
			a.symptoms,
			a.consultation_fee,
			a.payment_status,
			pp.full_name AS patient_name,
			pp.age,
			pp.gender,
			pp.phone AS patient_phone
		FROM `tabAppointment` a
		LEFT JOIN `tabPatient Profile` pp ON pp.name = a.patient
		WHERE a.doctor = %(doctor)s
		ORDER BY a.appointment_date DESC, a.appointment_time DESC
		""",
		{"doctor": doctor.name},
		as_dict=True,
	)

	def _dt(appt):
		time_val = appt.appointment_time or "00:00:00"
		try:
			return frappe.utils.get_datetime(f"{appt.appointment_date} {time_val}")
		except Exception:
			return None

	stats = {
		"total": len(appointments),
		"pending": 0,
		"confirmed": 0,
		"completed": 0,
		"cancelled": 0,
		"today": 0,
		"upcoming": 0,
		"earnings": 0,
	}

	today_appointments = []
	upcoming = []

	for appt in appointments:
		status = (appt.status or "").strip().lower()
		if status in stats:
			stats[status] += 1

		is_today = str(appt.appointment_date) == today_str
		if is_today:
			stats["today"] += 1
			today_appointments.append(appt)

		appt_dt = _dt(appt)
		if (
			status in ("pending", "confirmed")
			and appt_dt
			and appt_dt >= now
		):
			stats["upcoming"] += 1
			upcoming.append(appt)

		if status == "completed":
			stats["earnings"] += float(appt.consultation_fee or 0)

	# Sort today's schedule by time ascending (next first).
	today_appointments.sort(key=lambda a: str(a.appointment_time or ""))
	# Upcoming sorted chronologically.
	upcoming.sort(key=lambda a: str(a.appointment_date) + str(a.appointment_time or ""))

	unique_patients = {}
	for appt in appointments:
		if appt.patient:
			unique_patients.setdefault(
				appt.patient,
				{
					"name": appt.patient,
					"full_name": appt.patient_name,
					"age": appt.age,
					"gender": appt.gender,
					"phone": appt.patient_phone,
				},
			)

	return {
		"doctor": doctor,
		"stats": stats,
		"unique_patients": len(unique_patients),
		"today_appointments": today_appointments,
		"upcoming_appointments": upcoming[:6],
		"recent_patients": list(unique_patients.values())[:6],
	}


@frappe.whitelist()
def get_my_doctor_profile():
	"""Return the authenticated doctor's own profile."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in first"), frappe.AuthenticationError)

	doctor = _get_doctor_profile()
	if not doctor:
		frappe.throw(_("Doctor profile not found for this account"))
	return doctor
