"""
DocBook Patient Report API
Doctors order reports; lab/receptionist/patient upload them; uploaded reports
trigger queue-skip so the patient returns straight to the doctor.
"""

import frappe
from frappe import _

from docbook.api.access import (
	require_login, is_admin, is_laboratory, is_receptionist,
	current_doctor, current_patient, can_manage_reports,
)


REPORT_TYPES = ("Lab", "Imaging", "Prescription", "Document", "Other")


def _report_or_throw(report):
	row = frappe.db.get_value(
		"Patient Report",
		report,
		["name", "patient", "appointment", "referral", "ordered_by", "report_type",
		 "title", "laboratory", "external", "status", "report_file", "findings",
		 "description", "uploaded_by", "uploaded_at", "reviewed_by", "reviewed_at",
		 "sample_collected_at"],
		as_dict=True,
	)
	if not row:
		frappe.throw(_("Report '{0}' not found").format(report), frappe.DoesNotExistError)
	return row


def _link_file(file_url, doctype, name):
	"""Attach an uploaded File record to this document for auditability."""
	if not file_url:
		return
	try:
		file_docs = frappe.get_all(
			"File", filters={"file_url": file_url}, fields=["name"], limit=1
		)
		if file_docs:
			frappe.db.set_value("File", file_docs[0].name, {
				"attached_to_doctype": doctype, "attached_to_name": name,
			})
	except Exception:
		frappe.log_error(title="Link file failed", message=frappe.get_traceback())


# ---------------------------------------------------------------------------
# Order (doctor)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def order_report(appointment, report_type, title, description=None, laboratory=None):
	"""Doctor orders a report for an appointment. Moves the visit to
	'Report Pending' so the patient steps out of the queue until results."""
	require_login()
	doctor = current_doctor()
	if not doctor and not is_admin():
		frappe.throw(_("Only doctors can order reports"), frappe.PermissionError)

	appt = frappe.db.get_value(
		"Appointment", appointment,
		["name", "patient", "doctor", "referral", "status"], as_dict=True)
	if not appt:
		frappe.throw(_("Appointment not found"), frappe.DoesNotExistError)
	if not is_admin() and appt.doctor != doctor:
		frappe.throw(_("Not authorized to order reports on this appointment"),
			frappe.PermissionError)
	if report_type not in REPORT_TYPES:
		frappe.throw(_("Invalid report type"))
	if not title or not str(title).strip():
		frappe.throw(_("A report title is required"))

	report = frappe.get_doc({
		"doctype": "Patient Report",
		"patient": appt.patient,
		"appointment": appointment,
		"referral": appt.referral,
		"ordered_by": doctor or appt.doctor,
		"report_type": report_type,
		"title": title,
		"description": description or "",
		"laboratory": laboratory or "",
		"external": 0,
		"status": "Ordered",
	})
	report.insert(ignore_permissions=True)

	# Step the patient out of the active queue pending results.
	if appt.status in ("Pending", "Confirmed"):
		frappe.db.set_value("Appointment", appointment, "visit_stage", "Report Pending")

	frappe.db.commit()
	return {"success": True, "report": report.name, "status": "Ordered"}


@frappe.whitelist()
def mark_sample_collected(report):
	"""Lab marks a sample as collected / analysis in progress."""
	require_login()
	if not (is_laboratory() or is_receptionist() or is_admin()):
		frappe.throw(_("Not authorized"), frappe.PermissionError)
	row = _report_or_throw(report)
	if row.status not in ("Ordered", "Pending"):
		frappe.throw(_("Only ordered/pending reports can progress"))
	frappe.db.set_value("Patient Report", report, {
		"status": "Pending", "sample_collected_at": frappe.utils.now_datetime()})
	frappe.db.commit()
	return {"success": True, "status": "Pending"}


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

@frappe.whitelist()
def upload_report(report, file_url, findings=None, laboratory=None):
	"""
	Upload results to an existing ordered report. Lab, receptionist, doctor,
	or the owning patient may upload. Triggers the queue-skip transition
	(Ready For Review) via the PatientReport controller.
	"""
	require_login()
	row = _report_or_throw(report)

	# Authorization: lab/receptionist/admin, ordering/attending doctor, or the patient.
	doctor = current_doctor()
	patient = current_patient()
	allowed = (
		is_admin() or is_laboratory() or is_receptionist()
		or (doctor and doctor == row.ordered_by)
		or (patient and patient == row.patient)
	)
	if not allowed:
		frappe.throw(_("Not authorized to upload this report"), frappe.PermissionError)

	if row.status == "Reviewed":
		frappe.throw(_("This report has already been reviewed"))

	if not file_url and not findings:
		frappe.throw(_("A file or findings are required"))

	doc = frappe.get_doc("Patient Report", report)
	doc.status = "Uploaded"
	if file_url:
		doc.report_file = file_url
	if findings:
		doc.findings = findings
	if laboratory:
		doc.laboratory = laboratory
	doc.uploaded_by = frappe.session.user
	doc.uploaded_at = frappe.utils.now_datetime()
	doc.save(ignore_permissions=True)
	if file_url:
		_link_file(file_url, "Patient Report", report)

	frappe.db.commit()
	return {"success": True, "report": report, "status": "Uploaded"}


@frappe.whitelist()
def upload_external_report(
	appointment, file_url, report_type, title, findings=None, laboratory=None, description=None
):
	"""
	Self-upload an outside-hospital report directly onto an appointment.
	Used by patients (returning with a physical/digital result) and by
	receptionists registering a report brought to the front desk. Creates a
	new report already in 'Uploaded' state and triggers queue-skip.
	"""
	require_login()
	appt = frappe.db.get_value(
		"Appointment", appointment,
		["name", "patient", "doctor", "referral", "status"], as_dict=True)
	if not appt:
		frappe.throw(_("Appointment not found"), frappe.DoesNotExistError)

	doctor = current_doctor()
	patient = current_patient()
	allowed = (
		is_admin() or is_receptionist() or is_laboratory()
		or bool(doctor) or (patient and patient == appt.patient)
	)
	if not allowed:
		frappe.throw(_("Not authorized to upload a report for this appointment"),
			frappe.PermissionError)

	if report_type not in REPORT_TYPES:
		frappe.throw(_("Invalid report type"))
	if not title or not str(title).strip():
		frappe.throw(_("A report title is required"))

	report = frappe.get_doc({
		"doctype": "Patient Report",
		"patient": appt.patient,
		"appointment": appointment,
		"referral": appt.referral,
		"ordered_by": appt.doctor,
		"report_type": report_type,
		"title": title,
		"description": description or "",
		"laboratory": laboratory or "",
		"external": 1,
		"status": "Uploaded",
		"report_file": file_url or "",
		"findings": findings or "",
		"uploaded_by": frappe.session.user,
		"uploaded_at": frappe.utils.now_datetime(),
	})
	report.insert(ignore_permissions=True)
	if file_url:
		_link_file(file_url, "Patient Report", report.name)

	frappe.db.commit()
	return {"success": True, "report": report.name, "status": "Uploaded"}


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

REPORT_FIELDS = [
	"name", "patient", "appointment", "referral", "ordered_by", "report_type", "title",
	"laboratory", "external", "status", "report_file", "findings", "description",
	"uploaded_by", "uploaded_at", "reviewed_by", "reviewed_at", "sample_collected_at", "creation",
]


@frappe.whitelist()
def list_reports(appointment=None, referral=None, patient=None):
	"""Reports visible to the caller, optionally scoped to appointment/referral/patient."""
	require_login()
	doctor = current_doctor()
	self_patient = current_patient()

	if appointment:
		filters = {"appointment": appointment}
	elif referral:
		filters = {"referral": referral}
	elif patient:
		filters = {"patient": patient}
	elif doctor:
		# Reports on this doctor's appointments (incl. shared referral episodes).
		appts = [r.name for r in frappe.get_all("Appointment", filters={"doctor": doctor},
			fields=["name"])]
		ref_ids = [r.referral for r in frappe.get_all("Appointment",
			filters={"doctor": doctor, "referral": ["!=", ""]}, fields=["referral"]) if r.referral]
		or_filters = []
		if appts:
			or_filters.append(["appointment", "in", appts])
		if ref_ids:
			or_filters.append(["referral", "in", ref_ids])
		if not or_filters:
			return []
		return frappe.get_all("Patient Report", or_filters=or_filters,
			fields=REPORT_FIELDS, order_by="creation desc")
	elif self_patient:
		filters = {"patient": self_patient}
	elif is_receptionist() or is_laboratory() or is_admin():
		filters = {}
	else:
		return []

	return frappe.get_all("Patient Report", filters=filters,
		fields=REPORT_FIELDS, order_by="creation desc")


@frappe.whitelist()
def list_pending_reports():
	"""Lab worklist: ordered/pending reports awaiting upload."""
	require_login()
	if not (is_laboratory() or is_admin() or is_receptionist()):
		frappe.throw(_("Not authorized"), frappe.PermissionError)
	return frappe.get_all(
		"Patient Report",
		filters={"status": ["in", ["Ordered", "Pending"]]},
		fields=REPORT_FIELDS,
		order_by="creation asc",
	)


@frappe.whitelist()
def get_report(report):
	require_login()
	row = _report_or_throw(report)
	doctor = current_doctor()
	patient = current_patient()
	allowed = (
		is_admin() or is_laboratory() or is_receptionist()
		or (doctor and doctor == row.ordered_by)
		or (patient and patient == row.patient)
	)
	if not allowed:
		frappe.throw(_("Not authorized to view this report"), frappe.PermissionError)
	return row


# ---------------------------------------------------------------------------
# Review (doctor)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def mark_report_reviewed(report):
	"""Ordering/attending doctor marks an uploaded report as reviewed."""
	require_login()
	doctor = current_doctor()
	if not doctor and not is_admin():
		frappe.throw(_("Only doctors can review reports"), frappe.PermissionError)
	row = _report_or_throw(report)
	if row.status != "Uploaded":
		frappe.throw(_("Only uploaded reports can be reviewed"))
	frappe.db.set_value("Patient Report", report, {
		"status": "Reviewed", "reviewed_by": doctor or row.ordered_by,
		"reviewed_at": frappe.utils.now_datetime()})
	frappe.db.commit()
	return {"success": True, "status": "Reviewed"}


