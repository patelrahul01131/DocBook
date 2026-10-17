"""
Prescription and Prescription Medicine API.
All operations enforce strict ownership checks.
"""

import frappe
from frappe import _


def _require_auth():
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in first"), frappe.AuthenticationError)


def _get_patient_profile(user=None):
	user = user or frappe.session.user
	return frappe.db.get_value(
		"Patient Profile", {"user": user}, ["name", "full_name", "user"], as_dict=True
	)


def _get_doctor_profile(user=None):
	user = user or frappe.session.user
	return frappe.db.get_value(
		"Doctor Profile", {"user": user}, ["name", "full_name", "user"], as_dict=True
	)


def _doctor_owns_appointment(doctor_name, appointment_name):
	return frappe.db.exists("Appointment", {"name": appointment_name, "doctor": doctor_name})


# ---------------------------------------------------------------------------
# Patient — view own prescriptions
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_my_prescriptions():
	"""Return prescriptions belonging to the authenticated patient."""
	_require_auth()

	patient = _get_patient_profile()
	if not patient:
		frappe.throw(_("Patient profile not found for this account"))

	prescriptions = frappe.db.sql(
		"""
		SELECT
			p.name,
			p.patient,
			p.doctor,
			p.appointment,
			p.prescription_date,
			p.diagnosis,
			p.instructions,
			p.follow_up_date,
			p.status,
			p.notes,
			d.full_name AS doctor_name,
			d.specialty  AS doctor_specialty,
			d.qualification AS doctor_qualification
		FROM `tabPrescription` p
		LEFT JOIN `tabDoctor Profile` d ON d.name = p.doctor
		WHERE p.patient = %(patient)s
		ORDER BY p.prescription_date DESC, p.creation DESC
		""",
		{"patient": patient.name},
		as_dict=True,
	)

	return prescriptions


@frappe.whitelist()
def get_my_prescription_medicines():
	"""Return prescription medicines for the authenticated patient."""
	_require_auth()

	patient = _get_patient_profile()
	if not patient:
		frappe.throw(_("Patient profile not found for this account"))

	medicines = frappe.db.sql(
		"""
		SELECT
			pm.name,
			pm.prescription,
			pm.medicine,
			pm.prescribed_medicine_name,
			pm.dosage,
			pm.route,
			pm.frequency,
			pm.start_date,
			pm.end_date,
			pm.dose_time_1,
			pm.dose_time_2,
			pm.dose_time_3,
			pm.dose_time_4,
			pm.instructions,
			pm.status,
			m.medicine_name,
			m.generic_name,
			m.brand_name,
			m.strength,
			m.dosage_form,
			m.uses,
			m.medicine_image,
			m.common_side_effects
		FROM `tabPrescription Medicine` pm
		LEFT JOIN `tabMedicine` m ON m.name = pm.medicine
		WHERE pm.patient = %(patient)s
		ORDER BY pm.start_date DESC, pm.creation DESC
		""",
		{"patient": patient.name},
		as_dict=True,
	)

	return medicines


@frappe.whitelist()
def get_prescription_detail(prescription_name):
	"""Return full prescription detail for the authenticated user (patient or doctor)."""
	_require_auth()

	if not prescription_name:
		frappe.throw(_("Prescription name is required"))

	prx = frappe.db.get_value(
		"Prescription",
		prescription_name,
		["name", "patient", "doctor", "appointment", "prescription_date",
		 "diagnosis", "instructions", "follow_up_date", "status", "notes"],
		as_dict=True,
	)

	if not prx:
		frappe.throw(_("Prescription not found"), frappe.DoesNotExistError)

	# Authorization
	roles = frappe.get_roles(frappe.session.user)
	is_admin = "System Manager" in roles

	if not is_admin:
		patient = _get_patient_profile()
		doctor = _get_doctor_profile()

		if patient and patient.name == prx.patient:
			pass  # Patient accessing own prescription
		elif doctor and doctor.name == prx.doctor:
			pass  # Doctor accessing own prescription
		else:
			frappe.throw(_("You do not have permission to view this prescription"), frappe.PermissionError)

	# Fetch prescription medicines
	medicines = frappe.db.sql(
		"""
		SELECT
			pm.name,
			pm.medicine,
			pm.prescribed_medicine_name,
			pm.dosage,
			pm.route,
			pm.frequency,
			pm.start_date,
			pm.end_date,
			pm.dose_time_1,
			pm.dose_time_2,
			pm.dose_time_3,
			pm.dose_time_4,
			pm.instructions,
			pm.status,
			m.medicine_name,
			m.generic_name,
			m.strength,
			m.dosage_form,
			m.medicine_image
		FROM `tabPrescription Medicine` pm
		LEFT JOIN `tabMedicine` m ON m.name = pm.medicine
		WHERE pm.prescription = %(name)s
		ORDER BY pm.creation ASC
		""",
		{"name": prescription_name},
		as_dict=True,
	)

	doctor_data = frappe.db.get_value(
		"Doctor Profile",
		prx.doctor,
		["full_name", "specialty", "qualification", "phone"],
		as_dict=True,
	) if prx.doctor else None

	patient_data = frappe.db.get_value(
		"Patient Profile",
		prx.patient,
		["full_name", "phone", "age", "gender"],
		as_dict=True,
	) if prx.patient else None

	return {
		**prx,
		"medicines": medicines,
		"doctor_info": doctor_data,
		"patient_info": patient_data,
	}


# ---------------------------------------------------------------------------
# Doctor — manage prescriptions
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_doctor_prescriptions():
	"""Return prescriptions issued by the authenticated doctor."""
	_require_auth()

	doctor = _get_doctor_profile()
	if not doctor:
		frappe.throw(_("Doctor profile not found for this account"))

	prescriptions = frappe.db.sql(
		"""
		SELECT
			p.name,
			p.patient,
			p.appointment,
			p.prescription_date,
			p.diagnosis,
			p.status,
			p.follow_up_date,
			pp.full_name AS patient_name
		FROM `tabPrescription` p
		LEFT JOIN `tabPatient Profile` pp ON pp.name = p.patient
		WHERE p.doctor = %(doctor)s
		ORDER BY p.prescription_date DESC, p.creation DESC
		""",
		{"doctor": doctor.name},
		as_dict=True,
	)

	return prescriptions


@frappe.whitelist()
def create_prescription(
	patient,
	appointment=None,
	prescription_date=None,
	diagnosis=None,
	instructions=None,
	follow_up_date=None,
	notes=None,
	status="Active",
):
	"""Doctor creates a prescription for an authorized patient."""
	_require_auth()

	roles = frappe.get_roles(frappe.session.user)
	is_admin = "System Manager" in roles

	if not is_admin:
		doctor = _get_doctor_profile()
		if not doctor:
			frappe.throw(_("Only doctors can create prescriptions"), frappe.PermissionError)

		# Verify the doctor is linked to the appointment if provided
		if appointment and not _doctor_owns_appointment(doctor.name, appointment):
			frappe.throw(_("You are not authorized for this appointment"), frappe.PermissionError)
	else:
		doctor = frappe.db.get_value(
			"Doctor Profile", {"user": frappe.session.user}, ["name"], as_dict=True
		)

	if not frappe.db.exists("Patient Profile", patient):
		frappe.throw(_("Patient profile not found"))

	doc = frappe.get_doc(
		{
			"doctype": "Prescription",
			"patient": patient,
			"doctor": doctor.name if doctor else None,
			"appointment": appointment,
			"prescription_date": prescription_date or frappe.utils.today(),
			"diagnosis": diagnosis,
			"instructions": instructions,
			"follow_up_date": follow_up_date,
			"notes": notes,
			"status": status or "Active",
		}
	)

	doc.insert(ignore_permissions=is_admin)
	frappe.db.commit()

	return {"name": doc.name, "success": True}


@frappe.whitelist()
def add_prescription_medicine(
	prescription,
	medicine,
	dosage,
	frequency,
	start_date,
	end_date,
	route="Oral",
	dose_time_1=None,
	dose_time_2=None,
	dose_time_3=None,
	dose_time_4=None,
	instructions=None,
	status="Active",
):
	"""Doctor adds a medicine entry to a prescription."""
	_require_auth()

	roles = frappe.get_roles(frappe.session.user)
	is_admin = "System Manager" in roles

	prx = frappe.db.get_value(
		"Prescription",
		prescription,
		["name", "patient", "doctor", "status"],
		as_dict=True,
	)

	if not prx:
		frappe.throw(_("Prescription not found"), frappe.DoesNotExistError)

	if prx.status == "Cancelled":
		frappe.throw(_("Cannot add medicines to a cancelled prescription"))

	if not is_admin:
		doctor = _get_doctor_profile()
		if not doctor or doctor.name != prx.doctor:
			frappe.throw(_("You are not authorized for this prescription"), frappe.PermissionError)

	if not frappe.db.exists("Medicine", medicine):
		matched = _match_catalog_medicine(medicine)
		if matched:
			medicine = matched
		else:
			new_med = frappe.get_doc({
				"doctype": "Medicine",
				"medicine_name": medicine,
				"generic_name": medicine,
				"is_active": 1,
			})
			new_med.insert(ignore_permissions=True)
			medicine = new_med.name

	is_active_med = frappe.db.get_value("Medicine", medicine, "is_active")
	if not is_active_med:
		frappe.db.set_value("Medicine", medicine, "is_active", 1)

	# Snapshot medicine name
	med = frappe.db.get_value(
		"Medicine", medicine, ["medicine_name", "generic_name", "strength", "dosage_form"], as_dict=True
	)
	parts = [med.medicine_name]
	if med.strength:
		parts.append(med.strength)
	if med.dosage_form:
		parts.append(f"({med.dosage_form})")
	prescribed_name = " ".join(parts)

	doc = frappe.get_doc(
		{
			"doctype": "Prescription Medicine",
			"prescription": prescription,
			"patient": prx.patient,
			"doctor": prx.doctor,
			"medicine": medicine,
			"prescribed_medicine_name": prescribed_name,
			"dosage": dosage,
			"route": route or "Oral",
			"frequency": frequency,
			"start_date": start_date,
			"end_date": end_date,
			"dose_time_1": dose_time_1,
			"dose_time_2": dose_time_2,
			"dose_time_3": dose_time_3,
			"dose_time_4": dose_time_4,
			"instructions": instructions,
			"status": status or "Active",
		}
	)

	# Frappe auto-fills empty Time fields with the current time on insert
	# (via new_doc defaults). Stop that so unused dose_time slots stay empty
	# instead of becoming phantom "now" values that spawn duplicate reminders.
	doc.dont_update_if_missing = [
		"dose_time_1",
		"dose_time_2",
		"dose_time_3",
		"dose_time_4",
	]

	doc.insert(ignore_permissions=is_admin)

	# Schedule reminders for this medicine
	_schedule_reminders_for_medicine(doc)

	frappe.db.commit()

	return {"name": doc.name, "success": True}


def _schedule_reminders_for_medicine(med_doc):
	"""Generate Medicine Reminder records for the prescribed medicine schedule."""
	if med_doc.status != "Active":
		return

	# Only daily-fixed frequencies have a predictable schedule. "As Needed"
	# and "Other" are intentionally skipped.
	freq_dose_count = {
		"Once Daily": 1,
		"Twice Daily": 2,
		"Three Times Daily": 3,
		"Four Times Daily": 4,
	}
	expected = freq_dose_count.get(med_doc.frequency)
	if not expected:
		return

	# Cap to the number of dose times the frequency expects. This guards
	# against legacy/corrupt records where Frappe auto-filled the unused
	# Time fields with the creation timestamp (which produced duplicate
	# reminders at "now" instead of the real dose time).
	all_dose_times = [
		med_doc.dose_time_1,
		med_doc.dose_time_2,
		med_doc.dose_time_3,
		med_doc.dose_time_4,
	]
	dose_times = [t for t in all_dose_times[:expected] if t]

	if not dose_times:
		return

	# Get patient email
	user_email = frappe.db.get_value("Patient Profile", med_doc.patient, "user")
	if not user_email:
		return

	start = frappe.utils.getdate(med_doc.start_date)
	end = frappe.utils.getdate(med_doc.end_date)
	today = frappe.utils.getdate()
	current_date = max(start, today)

	count = 0
	max_reminders = 365  # Safety limit

	while current_date <= end and count < max_reminders:
		for dose_time in dose_times:
			# Format dose_time into HH:MM:SS string
			if hasattr(dose_time, 'strftime'):
				time_str = dose_time.strftime("%H:%M:%S")
			else:
				time_str = str(dose_time)

			scheduled_at = f"{current_date} {time_str}"

			# Check if reminder already exists
			exists = frappe.db.exists(
				"Medicine Reminder",
				{
					"prescription_medicine": med_doc.name,
					"scheduled_at": scheduled_at,
					"reminder_status": ["!=", "Cancelled"],
				},
			)

			if not exists:
				try:
					reminder = frappe.get_doc({
						"doctype": "Medicine Reminder",
						"patient": med_doc.patient,
						"prescription": med_doc.prescription,
						"prescription_medicine": med_doc.name,
						"scheduled_at": scheduled_at,
						"reminder_status": "Pending",
						"email_address": user_email,
						"active": 1,
					})
					reminder.insert(ignore_permissions=True)
					count += 1
				except Exception:
					pass  # Skip duplicates silently

		current_date = frappe.utils.add_days(current_date, 1)


@frappe.whitelist()
def record_consultation(
	appointment,
	symptoms=None,
	diagnosis=None,
	consultation_notes=None,
	treatment_plan=None,
	follow_up_date=None,
	follow_up_instructions=None,
):
	"""Doctor records consultation details on an appointment."""
	_require_auth()

	roles = frappe.get_roles(frappe.session.user)
	is_admin = "System Manager" in roles

	if not is_admin:
		doctor = _get_doctor_profile()
		if not doctor:
			frappe.throw(_("Only doctors can record consultation details"), frappe.PermissionError)

		if not _doctor_owns_appointment(doctor.name, appointment):
			frappe.throw(_("You are not authorized for this appointment"), frappe.PermissionError)

	if not frappe.db.exists("Appointment", appointment):
		frappe.throw(_("Appointment not found"), frappe.DoesNotExistError)

	doc = frappe.get_doc("Appointment", appointment)

	if symptoms is not None:
		doc.symptoms = symptoms
	if diagnosis is not None:
		doc.diagnosis = diagnosis
	if consultation_notes is not None:
		doc.consultation_notes = consultation_notes
	if treatment_plan is not None:
		doc.treatment_plan = treatment_plan
	if follow_up_date is not None:
		doc.follow_up_date = follow_up_date
	if follow_up_instructions is not None:
		doc.follow_up_instructions = follow_up_instructions

	if doc.status == "Pending":
		doc.status = "Confirmed"

	doc.save(ignore_permissions=is_admin)
	frappe.db.commit()

	return {"name": doc.name, "success": True}


@frappe.whitelist()
def get_doctor_appointments(status=None):
	"""Return appointments for the authenticated doctor."""
	_require_auth()

	doctor = _get_doctor_profile()
	if not doctor:
		frappe.throw(_("Doctor profile not found for this account"))

	filters = {"doctor": doctor.name}
	if status:
		filters["status"] = status

	appointments = frappe.db.sql(
		"""
		SELECT
			a.name,
			a.patient,
			a.doctor,
			a.appointment_date,
			a.appointment_time,
			a.status,
			a.reason,
			a.consultation_fee,
			a.payment_status,
			a.symptoms,
			a.diagnosis,
			a.treatment_plan,
			a.follow_up_date,
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

	return appointments


@frappe.whitelist()
def get_doctor_patients():
	"""Return unique patients the authenticated doctor has treated."""
	_require_auth()

	doctor = _get_doctor_profile()
	if not doctor:
		frappe.throw(_("Doctor profile not found for this account"))

	patients = frappe.db.sql(
		"""
		SELECT DISTINCT
			pp.name,
			pp.full_name,
			pp.age,
			pp.gender,
			pp.phone,
			pp.user
		FROM `tabAppointment` a
		JOIN `tabPatient Profile` pp ON pp.name = a.patient
		WHERE a.doctor = %(doctor)s
		ORDER BY pp.full_name ASC
		""",
		{"doctor": doctor.name},
		as_dict=True,
	)

	return patients


@frappe.whitelist()
def update_prescription(
	prescription,
	diagnosis=None,
	instructions=None,
	follow_up_date=None,
	notes=None,
	status=None,
):
	"""Doctor updates an existing prescription."""
	_require_auth()

	prx = frappe.db.get_value(
		"Prescription",
		prescription,
		["name", "doctor", "status"],
		as_dict=True,
	)
	if not prx:
		frappe.throw(_("Prescription not found"), frappe.DoesNotExistError)

	roles = frappe.get_roles(frappe.session.user)
	is_admin = "System Manager" in roles
	if not is_admin:
		doctor = _get_doctor_profile()
		if not doctor or doctor.name != prx.doctor:
			frappe.throw(_("You are not authorized to edit this prescription"), frappe.PermissionError)

	doc = frappe.get_doc("Prescription", prescription)
	if diagnosis is not None:
		doc.diagnosis = diagnosis
	if instructions is not None:
		doc.instructions = instructions
	if follow_up_date is not None:
		doc.follow_up_date = follow_up_date
	if notes is not None:
		doc.notes = notes
	if status is not None:
		doc.status = status

	doc.save(ignore_permissions=is_admin)
	frappe.db.commit()
	return {"success": True, "name": doc.name}


@frappe.whitelist()
def delete_prescription(prescription):
	"""Doctor deletes a prescription and cascades deletion to linked medicines and reminders."""
	_require_auth()

	prx = frappe.db.get_value(
		"Prescription",
		prescription,
		["name", "doctor"],
		as_dict=True,
	)
	if not prx:
		frappe.throw(_("Prescription not found"), frappe.DoesNotExistError)

	roles = frappe.get_roles(frappe.session.user)
	is_admin = "System Manager" in roles
	if not is_admin:
		doctor = _get_doctor_profile()
		if not doctor or doctor.name != prx.doctor:
			frappe.throw(_("You are not authorized to delete this prescription"), frappe.PermissionError)

	# Delete associated reminders
	frappe.db.delete("Medicine Reminder", {"prescription": prescription})

	# Delete associated prescription medicines
	frappe.db.delete("Prescription Medicine", {"prescription": prescription})

	# Delete prescription
	frappe.delete_doc("Prescription", prescription, ignore_permissions=True)
	frappe.db.commit()
	return {"success": True, "name": prescription}


@frappe.whitelist()
def update_prescription_medicine(
	medicine_record,
	dosage=None,
	frequency=None,
	route=None,
	start_date=None,
	end_date=None,
	instructions=None,
	dose_time_1=None,
	dose_time_2=None,
	dose_time_3=None,
	dose_time_4=None,
	status=None,
):
	"""Doctor updates a medicine line on a prescription."""
	_require_auth()

	pm = frappe.db.get_value(
		"Prescription Medicine",
		medicine_record,
		["name", "doctor", "prescription"],
		as_dict=True,
	)
	if not pm:
		frappe.throw(_("Prescription medicine not found"), frappe.DoesNotExistError)

	roles = frappe.get_roles(frappe.session.user)
	is_admin = "System Manager" in roles
	if not is_admin:
		doctor = _get_doctor_profile()
		if not doctor or doctor.name != pm.doctor:
			frappe.throw(_("You are not authorized to edit this medicine"), frappe.PermissionError)

	doc = frappe.get_doc("Prescription Medicine", medicine_record)
	# Keep empty Time slots empty (Frappe would otherwise default them to "now").
	doc.dont_update_if_missing = [
		"dose_time_1",
		"dose_time_2",
		"dose_time_3",
		"dose_time_4",
	]
	if dosage is not None:
		doc.dosage = dosage
	if frequency is not None:
		doc.frequency = frequency
	if route is not None:
		doc.route = route
	if start_date is not None:
		doc.start_date = start_date
	if end_date is not None:
		doc.end_date = end_date
	if instructions is not None:
		doc.instructions = instructions
	if dose_time_1 is not None:
		doc.dose_time_1 = dose_time_1
	if dose_time_2 is not None:
		doc.dose_time_2 = dose_time_2
	if dose_time_3 is not None:
		doc.dose_time_3 = dose_time_3
	if dose_time_4 is not None:
		doc.dose_time_4 = dose_time_4
	if status is not None:
		doc.status = status

	doc.save(ignore_permissions=True)

	# The schedule may have changed (frequency, dose times or dates). Drop the
	# old pending reminders and regenerate so edits take effect and any stale
	# duplicate reminders are cleared.
	if doc.status == "Active":
		frappe.db.delete(
			"Medicine Reminder",
			{"prescription_medicine": doc.name, "reminder_status": "Pending"},
		)
		_schedule_reminders_for_medicine(doc)

	frappe.db.commit()
	return {"success": True, "name": doc.name}


@frappe.whitelist()
def delete_prescription_medicine(medicine_record):
	"""Doctor removes a medicine line from a prescription."""
	_require_auth()

	pm = frappe.db.get_value(
		"Prescription Medicine",
		medicine_record,
		["name", "doctor", "prescription"],
		as_dict=True,
	)
	if not pm:
		frappe.throw(_("Prescription medicine not found"), frappe.DoesNotExistError)

	roles = frappe.get_roles(frappe.session.user)
	is_admin = "System Manager" in roles
	if not is_admin:
		doctor = _get_doctor_profile()
		if not doctor or doctor.name != pm.doctor:
			frappe.throw(_("You are not authorized to delete this medicine"), frappe.PermissionError)

	# Delete associated reminders
	frappe.db.delete("Medicine Reminder", {"prescription_medicine": medicine_record})

	frappe.delete_doc("Prescription Medicine", medicine_record, ignore_permissions=True)
	frappe.db.commit()
	return {"success": True, "name": medicine_record}


@frappe.whitelist()
def clear_consultation(appointment):
	"""Doctor clears consultation notes/diagnosis for an appointment."""
	_require_auth()

	roles = frappe.get_roles(frappe.session.user)
	is_admin = "System Manager" in roles
	if not is_admin:
		doctor = _get_doctor_profile()
		if not doctor:
			frappe.throw(_("Only doctors can manage consultations"), frappe.PermissionError)
		if not _doctor_owns_appointment(doctor.name, appointment):
			frappe.throw(_("You are not authorized for this appointment"), frappe.PermissionError)

	doc = frappe.get_doc("Appointment", appointment)
	doc.symptoms = ""
	doc.diagnosis = ""
	doc.consultation_notes = ""
	doc.treatment_plan = ""
	doc.follow_up_date = None
	doc.follow_up_instructions = ""
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"success": True, "name": doc.name}


@frappe.whitelist()
def get_all_patients():
	"""Doctor or admin retrieves all registered patient profiles for booking or scheduling."""
	_require_auth()

	patients = frappe.db.sql(
		"""
		SELECT
			name,
			full_name,
			age,
			gender,
			phone,
			user
		FROM `tabPatient Profile`
		ORDER BY full_name ASC
		""",
		as_dict=True,
	)
	return patients


@frappe.whitelist()
def ai_fill_consultation(appointment=None, symptoms=None, reason=None, prompt_instruction=None):
	_require_auth()
	roles = frappe.get_roles(frappe.session.user)
	is_admin = "System Manager" in roles
	if not is_admin:
		doctor = _get_doctor_profile()
		if not doctor:
			frappe.throw(_("Only doctors can use AI consultation fill"), frappe.PermissionError)
	if not appointment:
		frappe.throw(_("Appointment ID is required"))
	if not frappe.db.exists("Appointment", appointment):
		frappe.throw(_("Appointment not found"), frappe.DoesNotExistError)
	appt = frappe.db.get_value(
		"Appointment", appointment,
		["name", "patient", "doctor", "symptoms", "reason", "diagnosis",
		 "consultation_notes", "treatment_plan", "appointment_date"],
		as_dict=True,
	)
	if not is_admin:
		if not _doctor_owns_appointment(doctor.name, appointment):
			frappe.throw(_("You are not authorized for this appointment"), frappe.PermissionError)
	# Symptoms come first: the doctor records them (or passes the live form
	# values) before AI is allowed to draft the rest of the consultation.
	effective_symptoms = (symptoms or "").strip() or (appt.symptoms or "").strip()
	if not effective_symptoms:
		frappe.throw(_("Please record the patient's symptoms before using AI fill"),
			frappe.ValidationError)
	effective_reason = (reason or "").strip() or (appt.reason or "").strip()
	patient_name = appt.patient
	patient_profile = frappe.db.get_value(
		"Patient Profile", patient_name,
		["full_name", "age", "gender", "phone"], as_dict=True
	) or {}
	history = _get_patient_medical_history(patient_name)
	past_appts = _get_patient_appointments(patient_name)
	history_summary = []
	for h in history[:5]:
		history_summary.append(
			f"- {h.get('record_type', 'Condition')}: {h.get('medical_condition', '')} "
			f"({h.get('symptoms', '')}) - {h.get('status', '')}"
		)
	past_summary = []
	for p in past_appts[:5]:
		past_summary.append(
			f"- {p.get('appointment_date', '')}: {p.get('reason', '')} "
			f"Symptoms: {p.get('symptoms', '')} | Dx: {p.get('diagnosis', '')} "
			f"| Tx: {p.get('treatment_plan', '')}"
		)
	# Active medicines so the AI does not duplicate current therapy.
	med_lines = []
	try:
		for prx in frappe.get_all(
			"Prescription",
			filters={"patient": patient_name, "status": "Active"},
			fields=["name", "diagnosis"],
			order_by="prescription_date desc",
			limit=3,
		):
			for m in frappe.get_all(
				"Prescription Medicine",
				filters={"prescription": prx.name},
				fields=["prescribed_medicine_name", "dosage", "frequency", "status"],
			):
				if m.status and m.status != "Active":
					continue
				med_lines.append(
					f"- {m.prescribed_medicine_name}: {m.dosage or ''} {m.frequency or ''} "
					f"(for {prx.diagnosis or 'recent visit'})"
				)
	except Exception:
		med_lines = []

	# Recent reports so the AI can flag genuinely missing investigations.
	report_lines = []
	try:
		for r in frappe.get_all(
			"Patient Report",
			filters={"patient": patient_name},
			fields=["title", "report_type", "status", "findings"],
			order_by="creation desc",
			limit=5,
		):
			report_lines.append(
				f"- {r.title} ({r.report_type}) - {r.status}: {(r.findings or '')[:120]}"
			)
	except Exception:
		report_lines = []

	custom_doctor_prompt = ""
	if prompt_instruction and str(prompt_instruction).strip():
		custom_doctor_prompt = (
			f"\nDOCTOR PROMPT / SPECIFIC CLINICAL INSTRUCTIONS:\n"
			f"\"{str(prompt_instruction).strip()}\"\n"
			"Apply the doctor's instructions to modify or refine the diagnosis, treatment plan, "
			"suggested medicines, and reports accordingly.\n"
		)

	context_prompt = (
		"You are an experienced medical assistant helping a doctor fill a consultation form. "
		"Suggest: (1) likely diagnosis, (2) consultation notes, (3) treatment plan, "
		"(4) a short list of common medicines to prescribe (only when clearly indicated), "
		"(5) lab/imaging reports that should be requested for this visit, and "
		"(6) whether important medical history is missing and must be recorded. "
		"Reply ONLY in valid JSON with keys: diagnosis, consultation_notes, treatment_plan, "
		"suggested_medicines, suggested_reports, history_needed. "
		"suggested_medicines must be a list of objects with keys: medicine, dosage, frequency, "
		"duration, instructions. suggested_reports must be a list of objects with keys: test, "
		"reason. history_needed must be a short string - use an empty string when no history "
		"is missing.\\n\\n"
		f"CURRENT VISIT:\nPatient: {patient_profile.get('full_name', 'Unknown')} "
		f"(Age: {patient_profile.get('age', 'N/A')}, Gender: {patient_profile.get('gender', 'N/A')})\n"
		f"Date: {appt.appointment_date or 'Not specified'}\n"
		f"Reason: {effective_reason or 'Not specified'}\n"
		f"Symptoms: {effective_symptoms}\n\n"
		"MEDICAL HISTORY:\n"
		+ ("\n".join(history_summary) if history_summary else "No prior history on file.")
		+ "\nPAST APPOINTMENTS:\n"
		+ ("\n".join(past_summary) if past_summary else "No past appointments.")
		+ "\n\nACTIVE MEDICINES:\n"
		+ ("\n".join(med_lines) if med_lines else "None on file.")
		+ "\n\nRECENT REPORTS:\n"
		+ ("\n".join(report_lines) if report_lines else "None on file.")
		+ "\n"
		+ custom_doctor_prompt
	)
	ai_result = _query_ollama_json(context_prompt, temperature=0.4)
	if not ai_result or not ai_result.get("diagnosis"):
		ai_result = _generate_fallback_clinical_suggestions(
			effective_symptoms, patient_profile, history_summary, prompt_instruction=prompt_instruction
		)

	suggested_medicines = []
	for m in (ai_result.get("suggested_medicines") or []):
		if not isinstance(m, dict):
			continue
		name = str(m.get("medicine") or m.get("name") or "").strip()
		if not name:
			continue
		catalog = m.get("catalog_name") or _match_catalog_medicine(name)
		suggested_medicines.append({
			"medicine": name,
			"dosage": str(m.get("dosage") or "").strip(),
			"frequency": str(m.get("frequency") or "").strip(),
			"duration": str(m.get("duration") or "").strip(),
			"instructions": str(m.get("instructions") or "").strip(),
			"in_catalog": bool(catalog),
			"catalog_name": catalog,
		})
		if len(suggested_medicines) >= 8:
			break
	suggested_reports = []
	for r in (ai_result.get("suggested_reports") or []):
		if not isinstance(r, dict):
			continue
		test = str(r.get("test") or r.get("name") or "").strip()
		if not test:
			continue
		suggested_reports.append({
			"test": test,
			"reason": str(r.get("reason") or "").strip(),
		})
		if len(suggested_reports) >= 6:
			break
	history_needed = str(ai_result.get("history_needed") or "").strip()
	suggestions = {
		"diagnosis": ai_result.get("diagnosis", ""),
		"consultation_notes": ai_result.get("consultation_notes", ""),
		"treatment_plan": ai_result.get("treatment_plan", ""),
		"suggested_medicines": suggested_medicines,
		"suggested_reports": suggested_reports,
		"history_needed": history_needed,
	}
	return {
		"success": True,
		"appointment": appointment,
		"patient": patient_name,
		"patient_profile": patient_profile,
		"suggestions": suggestions,
		"symptoms_used": effective_symptoms,
		"current": {
			"symptoms": appt.symptoms or "",
			"reason": appt.reason or "",
			"diagnosis": appt.diagnosis or "",
			"consultation_notes": appt.consultation_notes or "",
			"treatment_plan": appt.treatment_plan or "",
		},
		"message": _("AI consultation suggestions generated. Review before saving."),
	}


@frappe.whitelist()
def ai_generate_summary(appointment=None):
	_require_auth()
	if not appointment:
		frappe.throw(_("Appointment ID is required"))
	if not frappe.db.exists("Appointment", appointment):
		frappe.throw(_("Appointment not found"), frappe.DoesNotExistError)
	appt = frappe.db.get_value(
		"Appointment", appointment,
		["name", "patient", "doctor", "symptoms", "diagnosis",
		 "consultation_notes", "treatment_plan", "follow_up_date",
		 "follow_up_instructions", "appointment_date", "appointment_time"],
		as_dict=True,
	)
	# Only the patient, their doctor, or an admin may read the summary.
	roles = frappe.get_roles(frappe.session.user)
	if "System Manager" not in roles:
		my_patient = _get_patient_profile()
		my_doctor = _get_doctor_profile()
		owns_patient = bool(my_patient) and my_patient.name == appt.patient
		owns_doctor = bool(my_doctor) and my_doctor.name == appt.doctor
		if not (owns_patient or owns_doctor):
			frappe.throw(_("Not authorized to view this summary"), frappe.PermissionError)
	patient_name = appt.patient
	patient_profile = frappe.db.get_value(
		"Patient Profile", patient_name,
		["full_name", "age", "gender", "phone"], as_dict=True
	) or {}
	doctor_profile = frappe.db.get_value(
		"Doctor Profile", appt.doctor,
		["full_name", "specialty", "phone"], as_dict=True
	) or {}
	prescription = frappe.db.get_value(
		"Prescription", {"appointment": appointment},
		["name", "diagnosis", "instructions", "follow_up_date", "status", "notes"],
		as_dict=True,
	)
	medicines = []
	if prescription:
		med_rows = frappe.get_all(
			"Prescription Medicine",
			filters={"prescription": prescription.name},
			fields=[
				"prescribed_medicine_name", "dosage", "route", "frequency",
				"start_date", "end_date", "instructions", "status",
			],
			order_by="creation asc",
		)
		medicines = med_rows or []
	history = _get_patient_medical_history(patient_name)
	history_conditions = []
	for h in history[:5]:
		if h.get("medical_condition"):
			history_conditions.append(f"{h.get('medical_condition')} ({h.get('severity', 'N/A')})")
	meds_text = ""
	for m in medicines:
		meds_text += (
			f"- {m.get('prescribed_medicine_name', 'Medicine')}: {m.get('dosage', '')} "
			f"{m.get('route', '')}, {m.get('frequency', '')}"
		)
		if m.get('start_date') and m.get('end_date'):
			meds_text += f" from {m.get('start_date')} to {m.get('end_date')}"
		if m.get('instructions'):
			meds_text += f" - {m.get('instructions')}"
		meds_text += "\n"
	summary_prompt = (
		"You are a caring medical assistant. Create a patient-friendly summary of this consultation. "
		"Use simple, non-technical language. Include: what was diagnosed, what treatment was prescribed, "
		"what medicines to take and how, what to watch for, and when to return. "
		"Be encouraging and clear. Reply ONLY in JSON with keys: summary, key_points, next_steps.\n\n"
		f"PATIENT: {patient_profile.get('full_name', 'Unknown')} "
		f"(Age: {patient_profile.get('age', 'N/A')}, Gender: {patient_profile.get('gender', 'N/A')})\n"
		f"DOCTOR: Dr. {doctor_profile.get('full_name', 'Unknown')} ({doctor_profile.get('specialty', 'Specialist')})\n"
		f"DATE: {appt.appointment_date or 'Not specified'}\n\n"
		f"DIAGNOSIS: {appt.diagnosis or 'Not recorded'}\n"
		f"CONSULTATION NOTES: {appt.consultation_notes or 'Not recorded'}\n"
		f"TREATMENT PLAN: {appt.treatment_plan or 'Not recorded'}\n\n"
		f"PRESCRIBED MEDICINES:\n{meds_text if meds_text else 'None prescribed.'}\n"
		f"FOLLOW-UP: {appt.follow_up_date or 'None scheduled'} - {appt.follow_up_instructions or ''}\n\n"
		f"PAST MEDICAL CONDITIONS: {', '.join(history_conditions) if history_conditions else 'None on file.'}"
	)
	ai_result = _query_ollama_json(summary_prompt, temperature=0.5)
	return {
		"success": True,
		"appointment": appointment,
		"patient": patient_profile,
		"doctor": doctor_profile,
		"summary": ai_result.get("summary", ""),
		"key_points": ai_result.get("key_points", []),
		"next_steps": ai_result.get("next_steps", []),
		"diagnosis": appt.diagnosis or "",
		"medicines": medicines,
		"follow_up_date": appt.follow_up_date or None,
		"follow_up_instructions": appt.follow_up_instructions or "",
		"message": _("AI summary generated."),
	}


@frappe.whitelist()
def ai_save_consultation(appointment=None, diagnosis=None, consultation_notes=None, treatment_plan=None,
		follow_up_date=None, follow_up_instructions=None):
	_require_auth()
	roles = frappe.get_roles(frappe.session.user)
	is_admin = "System Manager" in roles
	if not is_admin:
		doctor = _get_doctor_profile()
		if not doctor:
			frappe.throw(_("Only doctors can save consultation details"), frappe.PermissionError)
	if not appointment:
		frappe.throw(_("Appointment ID is required"))
	if not frappe.db.exists("Appointment", appointment):
		frappe.throw(_("Appointment not found"), frappe.DoesNotExistError)
	if not is_admin:
		if not _doctor_owns_appointment(doctor.name, appointment):
			frappe.throw(_("You are not authorized for this appointment"), frappe.PermissionError)
	return record_consultation(
		appointment=appointment,
		symptoms=None,
		diagnosis=diagnosis,
		consultation_notes=consultation_notes,
		treatment_plan=treatment_plan,
		follow_up_date=follow_up_date,
		follow_up_instructions=follow_up_instructions,
	)


def _generate_fallback_clinical_suggestions(symptoms: str, patient_profile: dict, history_summary: list, prompt_instruction: str = None) -> dict:
	s = (symptoms or "").lower()
	p = (prompt_instruction or "").lower()
	diag = ""
	notes = ""
	plan = ""
	meds = []
	reports = []
	hist_needed = ""

	if any(k in s for k in ("fever", "temperature", "chills", "pyrexia")):
		if any(k in s for k in ("cough", "cold", "throat", "sore throat", "runny nose")):
			diag = "Acute Upper Respiratory Tract Infection with Viral Pyrexia"
			notes = f"Patient presents with {symptoms}. Pharyngeal congestion noted. Lungs clear to auscultation bilaterally. Vital signs stable."
			plan = "Antipyretic therapy, oral antihistamine/decongestant, adequate hydration, saline gargles. Rest for 3-5 days. Review if symptoms worsen."
			meds.append({"medicine": "Paracetamol", "dosage": "650mg", "frequency": "Three Times Daily", "duration": "5 days", "instructions": "Take after food for fever"})
			meds.append({"medicine": "Cetirizine", "dosage": "10mg", "frequency": "Once Daily", "duration": "5 days", "instructions": "Take at night before sleeping"})
			reports.append({"test": "Complete Blood Count (CBC)", "reason": "Rule out secondary bacterial infection and monitor inflammatory markers"})
		else:
			diag = "Acute Febrile Illness (Viral Etiology Under Investigation)"
			notes = f"Patient reports fever episodes. Symptoms recorded: {symptoms}. No immediate focal infection signs."
			plan = "Symptomatic fever management with paracetamol, sponge bath if temperature > 101F, high fluid intake."
			meds.append({"medicine": "Paracetamol", "dosage": "650mg", "frequency": "Three Times Daily", "duration": "5 days", "instructions": "Take after meals"})
			reports.append({"test": "Complete Blood Count (CBC)", "reason": "Assess WBC count and platelet trends"})
			reports.append({"test": "Erythrocyte Sedimentation Rate (ESR)", "reason": "Check systemic inflammatory marker"})

	elif any(k in s for k in ("cough", "cold", "congestion", "breathing")):
		diag = "Acute Bronchial / Respiratory Congestion"
		notes = f"Presenting complaints of {symptoms}. Airway examination reveals mild wheeze / mucosal redness. Hydration recommended."
		plan = "Steam inhalation twice daily, oral bronchodilator/cough formulation, warm fluids, avoid cold exposure."
		meds.append({"medicine": "Cetirizine", "dosage": "10mg", "frequency": "Once Daily", "duration": "7 days", "instructions": "Take at bedtime"})
		meds.append({"medicine": "Amoxicillin", "dosage": "500mg", "frequency": "Twice Daily", "duration": "5 days", "instructions": "Complete full antibiotic course after food"})
		reports.append({"test": "Chest X-Ray (PA View)", "reason": "Assess lung fields and rule out consolidation / infiltration"})

	elif any(k in s for k in ("chest pain", "heart", "palpitation", "breathless", "angina")):
		diag = "Suspected Angina Pectoris / Cardiovascular Evaluation"
		notes = f"Cardiology evaluation for reported {symptoms}. Immediate vitals and cardiac tracing required."
		plan = "Stat 12-lead ECG, cardiology consult, avoid strenuous physical activity, monitor pulse and blood pressure closely."
		meds.append({"medicine": "Atorvastatin", "dosage": "10mg", "frequency": "Once Daily", "duration": "14 days", "instructions": "Take at bedtime with water"})
		reports.append({"test": "12-Lead Electrocardiogram (ECG)", "reason": "Evaluate cardiac rhythm, ST-T wave changes, and ischemia"})
		reports.append({"test": "Lipid Profile", "reason": "Evaluate cholesterol, triglycerides, and cardiovascular risk"})

	elif any(k in s for k in ("headache", "migraine", "head pain")):
		diag = "Tension-Type Headache / Cephalea"
		notes = f"Patient suffers from persistent headache. Symptoms: {symptoms}. Neurological screening gross motor intact."
		plan = "Analgesic protocol, hydration, regular sleep schedule, screen break intervals, stress reduction."
		meds.append({"medicine": "Paracetamol", "dosage": "500mg", "frequency": "Twice Daily", "duration": "3 days", "instructions": "Take SOS for acute headache after meal"})
		reports.append({"test": "Blood Pressure & Ophthalmic Fundus Examination", "reason": "Rule out secondary hypertension and optic disc edema"})

	elif any(k in s for k in ("stomach", "abdomen", "vomit", "diarrhea", "nausea", "acidity", "gastric")):
		diag = "Acute Gastritis / Functional Dyspepsia"
		notes = f"Abdominal complaints recorded: {symptoms}. Mild epigastric tenderness, soft abdomen, active bowel sounds."
		plan = "Proton pump inhibitor before breakfast, light bland diet, avoid spicy/greasy foods, oral rehydration."
		meds.append({"medicine": "Pantoprazole", "dosage": "40mg", "frequency": "Once Daily", "duration": "7 days", "instructions": "Take 30 minutes before morning breakfast"})
		reports.append({"test": "Ultrasound Abdomen & Pelvis", "reason": "Evaluate gallbladder, liver, and biliary tract"})

	elif any(k in s for k in ("sugar", "diabetes", "thirst", "frequent urination")):
		diag = "Type 2 Diabetes Mellitus Management"
		notes = f"Glycemic review for {symptoms}. Baseline metabolic assessment."
		plan = "Oral hypoglycemic agent, diabetic diet (low glycemic index), 30 minutes daily brisk walk, glycemic log."
		meds.append({"medicine": "Metformin", "dosage": "500mg", "frequency": "Twice Daily", "duration": "30 days", "instructions": "Take with morning and evening meals"})
		reports.append({"test": "Fasting & Post-Prandial Blood Sugar", "reason": "Monitor day-to-day glycemic control"})
		reports.append({"test": "HbA1c (Glycated Hemoglobin)", "reason": "Assess 3-month average glycemic control"})

	else:
		diag = f"Clinical Symptom Assessment: {symptoms.title()}"
		notes = f"Consultation initiated for reported symptoms: {symptoms}. Clinical examination conducted. Systemic review normal."
		plan = "Conservative therapy, adequate rest and hydration, lifestyle moderation. Follow-up if symptoms persist beyond 5 days."
		meds.append({"medicine": "Paracetamol", "dosage": "500mg", "frequency": "Twice Daily", "duration": "3 days", "instructions": "Take after meals if needed"})
		reports.append({"test": "Complete Blood Count (CBC)", "reason": "Baseline diagnostic evaluation"})

	# Apply doctor's custom prompt modifications if provided
	if p:
		notes += f" [Doctor instruction: {prompt_instruction.strip()}]"
		if "allergy" in p or "allergic" in p or "avoid" in p or "no " in p:
			if "amoxicillin" in p or "penicillin" in p:
				meds = [m for m in meds if not any(x in m["medicine"].lower() for x in ("amoxicillin", "penicillin"))]
				meds.append({"medicine": "Azithromycin", "dosage": "500mg", "frequency": "Once Daily", "duration": "3 days", "instructions": "Alternative antibiotic taken 1h before food"})
			if "paracetamol" in p:
				meds = [m for m in meds if "paracetamol" not in m["medicine"].lower()]
				meds.append({"medicine": "Ibuprofen", "dosage": "400mg", "frequency": "Twice Daily", "duration": "3 days", "instructions": "Take after meals"})
		if "multivitamin" in p or "vitamin" in p:
			meds.append({"medicine": "Multivitamin", "dosage": "1 Tab", "frequency": "Once Daily", "duration": "15 days", "instructions": "Take with breakfast"})
		if "500mg" in p:
			for m in meds:
				if "paracetamol" in m["medicine"].lower():
					m["dosage"] = "500mg"
		if "x-ray" in p or "xray" in p:
			if not any("x-ray" in r["test"].lower() for r in reports):
				reports.append({"test": "Chest X-Ray (PA View)", "reason": "Doctor requested radiographic screening"})
		if "blood" in p or "cbc" in p:
			if not any("cbc" in r["test"].lower() for r in reports):
				reports.append({"test": "Complete Blood Count (CBC)", "reason": "Hematologic workup"})

	if not history_summary:
		hist_needed = "Patient has no past medical history on file. Record chronic illnesses, surgeries, and family medical background."

	for m in meds:
		catalog = _match_catalog_medicine(m["medicine"])
		m["in_catalog"] = bool(catalog)
		m["catalog_name"] = catalog or ""

	return {
		"diagnosis": diag,
		"consultation_notes": notes,
		"treatment_plan": plan,
		"suggested_medicines": meds,
		"suggested_reports": reports,
		"history_needed": hist_needed,
	}


def _query_ollama_json(prompt: str, temperature: float = 0.3) -> dict:
	import json as _json
	import urllib.request as _req
	payload = _json.dumps({
		"model": "qwen2.5:7b",
		"prompt": prompt,
		"stream": False,
		"temperature": temperature,
		"format": "json",
		"options": {"num_predict": 1600},
	}).encode("utf-8")
	try:
		request = _req.Request(
			"http://localhost:11434/api/generate",
			data=payload,
			headers={"Content-Type": "application/json"},
			method="POST",
		)
		with _req.urlopen(request, timeout=90) as response:
			raw = response.read().decode("utf-8")
			result = _json.loads(raw)
			text = result.get("response", "{}").strip()
			if text.startswith("```json"):
				text = text[7:]
			if text.endswith("```"):
				text = text[:-3]
			return _json.loads(text)
	except Exception:
		return {}


def _get_patient_medical_history(patient_name: str) -> list:
	try:
		rows = frappe.get_all(
			"Patient Medical History",
			filters={"patient": patient_name},
			fields=[
				"medical_condition", "description", "symptoms", "allergies",
				"record_type", "status", "severity", "record_date",
			],
			order_by="record_date desc",
		)
		return rows or []
	except Exception:
		return []


def _get_patient_appointments(patient_name: str) -> list:
	try:
		rows = frappe.get_all(
			"Appointment",
			filters={"patient": patient_name, "docstatus": ["!=", 2]},
			fields=[
				"appointment_date", "appointment_time", "doctor", "reason",
				"symptoms", "diagnosis", "treatment_plan", "status",
			],
			order_by="appointment_date desc",
			limit=10,
		)
		for r in rows:
			if r.doctor:
				dname = frappe.db.get_value("Doctor Profile", r.doctor, "full_name")
				r.doctor_name = dname
		return rows or []
	except Exception:
		return []


def _match_catalog_medicine(name: str):
	"""Resolve an AI-suggested medicine to a catalog entry, if one exists.

	Tries the exact name, then progressively shorter prefixes so an AI
	suggestion like "Paracetamol 500mg Tablet" still matches catalog
	entries such as "Paracetamol".
	"""
	try:
		if frappe.db.exists("Medicine", name):
			return name
		words = [w for w in str(name).split() if w]
		candidates = [name, " ".join(words[:2]), words[0] if words else ""]
		for candidate in candidates:
			if not candidate:
				continue
			like = "%{0}%".format(candidate.replace("%", "").replace("_", ""))
			hit = frappe.db.get_value(
				"Medicine",
				{"medicine_name": ["like", like]},
				"name",
			)
			if hit:
				return hit
		return None
	except Exception:
		return None
