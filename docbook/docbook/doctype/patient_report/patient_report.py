# Copyright (c) 2026, Rahul and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


VALID_STATUSES = ("Ordered", "Pending", "Uploaded", "Reviewed", "Cancelled")
VALID_TYPES = ("Lab", "Imaging", "Prescription", "Document", "Other")


class PatientReport(Document):
	def validate(self):
		"""Integrity checks for a patient report."""
		if self.status and self.status not in VALID_STATUSES:
			frappe.throw(_("Invalid report status: {0}").format(self.status))

		if self.report_type and self.report_type not in VALID_TYPES:
			frappe.throw(_("Invalid report type: {0}").format(self.report_type))

		if not self.appointment and not self.referral:
			frappe.throw(_("A report must be linked to an appointment or a referral"))

		# Patient consistency with the linked appointment.
		if self.appointment:
			appt_patient = frappe.db.get_value("Appointment", self.appointment, "patient")
			if appt_patient and self.patient and appt_patient != self.patient:
				frappe.throw(
					_("Appointment {0} does not belong to this patient").format(self.appointment)
				)

		if self.status == "Uploaded" and not self.uploaded_at:
			self.uploaded_at = frappe.utils.now_datetime()
			if not self.uploaded_by:
				self.uploaded_by = frappe.session.user

	def on_update(self):
		prev = self.get_doc_before_save()
		prev_status = prev.status if prev else None

		if self.status == "Uploaded" and prev_status != "Uploaded":
			self._on_report_uploaded()

		if self.status == "Reviewed" and prev_status != "Reviewed":
			if not self.reviewed_at:
				frappe.db.set_value(self.doctype, self.name, "reviewed_at", frappe.utils.now_datetime())

	def _on_report_uploaded(self):
		"""Queue-skip: a completed report returns the patient to the doctor
		without re-entering the waiting queue."""
		appt = self.appointment
		if not appt or not frappe.db.exists("Appointment", appt):
			return

		frappe.db.set_value(
			"Appointment",
			appt,
			{
				"visit_stage": "Ready For Review",
				"priority": 1,
				"checked_in": 1,
				"checked_in_at": frappe.utils.now_datetime(),
			},
		)

		# Notify the ordering doctor (best-effort).
		try:
			ordered_by = self.ordered_by or frappe.db.get_value("Appointment", appt, "doctor")
			if ordered_by:
				doctor_user = frappe.db.get_value("Doctor Profile", ordered_by, "user")
				if doctor_user and doctor_user != "Guest":
					frappe.sendmail(
						recipients=[doctor_user],
						subject=_("Report ready for review: {0}").format(self.title or self.name),
						message=_(
							"A report '{title}' for patient {patient} has been uploaded and is ready for review."
						).format(title=self.title or self.name, patient=self.patient),
					)
		except Exception:
			frappe.log_error(title="Report upload notification failed", message=frappe.get_traceback())
