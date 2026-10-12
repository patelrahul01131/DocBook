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
		frappe.throw(_("Medicine not found"))

	is_active_med = frappe.db.get_value("Medicine", medicine, "is_active")
	if not is_active_med:
		frappe.throw(_("Medicine is not active and cannot be prescribed"))

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

	doc.insert(ignore_permissions=is_admin)

	# Schedule reminders for this medicine
	_schedule_reminders_for_medicine(doc)

	frappe.db.commit()

	return {"name": doc.name, "success": True}


def _schedule_reminders_for_medicine(med_doc):
	"""Generate Medicine Reminder records for the prescribed medicine schedule."""
	if med_doc.frequency == "As Needed" or med_doc.status != "Active":
		return

	dose_times = [
		med_doc.dose_time_1,
		med_doc.dose_time_2,
		med_doc.dose_time_3,
		med_doc.dose_time_4,
	]
	dose_times = [t for t in dose_times if t]

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

