"""
Medical history API — patient and doctor endpoints.
Strict ownership checks enforced on every call.
"""

import frappe
from frappe import _


def _require_auth():
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in first"), frappe.AuthenticationError)


def _get_patient_profile(user=None):
	user = user or frappe.session.user
	patient = frappe.db.get_value(
		"Patient Profile", {"user": user}, ["name", "full_name", "user"], as_dict=True
	)
	return patient


def _get_doctor_profile(user=None):
	user = user or frappe.session.user
	doctor = frappe.db.get_value(
		"Doctor Profile", {"user": user}, ["name", "full_name", "user"], as_dict=True
	)
	return doctor


def _doctor_treats_patient(doctor_name, patient_name):
	"""Return True if the doctor has at least one appointment with this patient."""
	return frappe.db.exists(
		"Appointment",
		{
			"doctor": doctor_name,
			"patient": patient_name,
			"status": ["!=", "Cancelled"],
		},
	)


# ---------------------------------------------------------------------------
# Patient views
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_my_medical_history():
	"""Return the authenticated patient's own medical history records."""
	_require_auth()

	patient = _get_patient_profile()
	if not patient:
		frappe.throw(_("Patient profile not found for this account"))

	records = frappe.db.sql(
		"""
		SELECT
			h.name,
			h.record_date,
			h.record_type,
			h.medical_condition,
			h.condition,
			h.description,
			h.symptoms,
			h.allergies,
			h.current_medications,
			h.past_treatments,
			h.treatment_notes,
			h.status,
			h.severity,
			h.diagnosis_date,
			h.appointment,
			h.recorded_by,
			u.full_name AS recorded_by_name
		FROM `tabPatient Medical History` h
		LEFT JOIN `tabUser` u ON u.name = h.recorded_by
		WHERE h.patient = %(patient)s
		ORDER BY h.record_date DESC, h.creation DESC
		""",
		{"patient": patient.name},
		as_dict=True,
	)

	return records


# ---------------------------------------------------------------------------
# Doctor views
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_patient_medical_history(patient):
	"""
	Return medical history for a patient — only for doctors who have treated them.
	"""
	_require_auth()

	if not patient:
		frappe.throw(_("Patient is required"))

	roles = frappe.get_roles(frappe.session.user)
	is_admin = "System Manager" in roles

	if not is_admin:
		doctor = _get_doctor_profile()
		if not doctor:
			frappe.throw(_("Only doctors can access patient medical history"), frappe.PermissionError)

		if not _doctor_treats_patient(doctor.name, patient):
			frappe.throw(
				_("You do not have permission to view this patient's history"),
				frappe.PermissionError,
			)

	records = frappe.db.sql(
		"""
		SELECT
			h.name,
			h.record_date,
			h.record_type,
			h.medical_condition,
			h.condition,
			h.description,
			h.symptoms,
			h.allergies,
			h.current_medications,
			h.past_treatments,
			h.treatment_notes,
			h.status,
			h.severity,
			h.diagnosis_date,
			h.appointment,
			h.recorded_by,
			u.full_name AS recorded_by_name
		FROM `tabPatient Medical History` h
		LEFT JOIN `tabUser` u ON u.name = h.recorded_by
		WHERE h.patient = %(patient)s
		ORDER BY h.record_date DESC, h.creation DESC
		""",
		{"patient": patient},
		as_dict=True,
	)

	return records


@frappe.whitelist()
def create_medical_history_record(
	patient,
	record_date,
	medical_condition,
	status="Active",
	severity=None,
	description=None,
	symptoms=None,
	allergies=None,
	current_medications=None,
	past_treatments=None,
	treatment_notes=None,
	notes=None,
	appointment=None,
	record_type="Medical Condition",
):
	"""Doctor creates a new medical history record for an authorized patient."""
	_require_auth()

	roles = frappe.get_roles(frappe.session.user)
	is_admin = "System Manager" in roles

	if not is_admin:
		patient_prof = _get_patient_profile()
		doctor = _get_doctor_profile()
		is_own_patient = patient_prof and patient_prof.name == patient
		is_treating_doctor = doctor and _doctor_treats_patient(doctor.name, patient)

		if not (is_own_patient or is_treating_doctor):
			frappe.throw(
				_("You do not have permission to add records for this patient"),
				frappe.PermissionError,
			)

	if not frappe.db.exists("Patient Profile", patient):
		frappe.throw(_("Patient profile not found"))

	doc = frappe.get_doc(
		{
			"doctype": "Patient Medical History",
			"patient": patient,
			"record_date": record_date or frappe.utils.today(),
			"record_type": record_type or "Medical Condition",
			"medical_condition": medical_condition,
			"condition": medical_condition,
			"status": status or "Active",
			"severity": severity,
			"description": description,
			"symptoms": symptoms,
			"allergies": allergies,
			"current_medications": current_medications,
			"past_treatments": past_treatments,
			"treatment_notes": treatment_notes,
			"notes": notes,
			"appointment": appointment,
			"recorded_by": frappe.session.user,
		}
	)

	doc.insert(ignore_permissions=True)
	frappe.db.commit()

	return {"name": doc.name, "success": True}


@frappe.whitelist()
def update_medical_history_record(record_name, **kwargs):
	"""Doctor or patient updates an existing medical history record."""
	_require_auth()

	if not frappe.db.exists("Patient Medical History", record_name):
		frappe.throw(_("Record not found"), frappe.DoesNotExistError)

	doc = frappe.get_doc("Patient Medical History", record_name)

	roles = frappe.get_roles(frappe.session.user)
	is_admin = "System Manager" in roles

	if not is_admin:
		patient_prof = _get_patient_profile()
		doctor = _get_doctor_profile()
		is_own_patient = patient_prof and patient_prof.name == doc.patient
		is_treating_doctor = doctor and _doctor_treats_patient(doctor.name, doc.patient)

		if not (is_own_patient or is_treating_doctor):
			frappe.throw(
				_("You do not have permission to update this record"),
				frappe.PermissionError,
			)

	allowed = [
		"medical_condition", "condition", "status", "severity", "description",
		"symptoms", "allergies", "current_medications", "past_treatments",
		"treatment_notes", "notes", "record_type", "diagnosis_date", "record_date",
	]

	for key, value in kwargs.items():
		if key in allowed:
			setattr(doc, key, value)

	# Keep the two condition fields in sync
	if doc.medical_condition and not doc.condition:
		doc.condition = doc.medical_condition
	elif doc.condition and not doc.medical_condition:
		doc.medical_condition = doc.condition

	doc.save(ignore_permissions=True)
	frappe.db.commit()

	return {"name": doc.name, "success": True}


@frappe.whitelist()
def delete_medical_history_record(record_name):
	"""Doctor or patient deletes an existing medical history record."""
	_require_auth()

	if not frappe.db.exists("Patient Medical History", record_name):
		frappe.throw(_("Record not found"), frappe.DoesNotExistError)

	doc = frappe.get_doc("Patient Medical History", record_name)

	roles = frappe.get_roles(frappe.session.user)
	is_admin = "System Manager" in roles

	if not is_admin:
		patient_prof = _get_patient_profile()
		doctor = _get_doctor_profile()
		is_own_patient = patient_prof and patient_prof.name == doc.patient
		is_treating_doctor = doctor and _doctor_treats_patient(doctor.name, doc.patient)

		if not (is_own_patient or is_treating_doctor):
			frappe.throw(
				_("You do not have permission to delete this record"),
				frappe.PermissionError,
			)

	frappe.delete_doc("Patient Medical History", record_name, ignore_permissions=True)
	frappe.db.commit()

	return {"success": True, "name": record_name}

