# Copyright (c) 2026, Rahul and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class PatientMedicalHistory(Document):
	def validate(self):
		if not self.patient:
			frappe.throw(_("Patient is required"))

		if not frappe.db.exists("Patient Profile", self.patient):
			frappe.throw(_("Patient Profile does not exist"))

		# Synchronize medical_condition and condition for backward compatibility
		if self.medical_condition and not self.condition:
			self.condition = self.medical_condition
		elif self.condition and not self.medical_condition:
			self.medical_condition = self.condition

		if not self.medical_condition and not self.condition:
			frappe.throw(_("Medical condition is required"))

		if not self.record_date:
			self.record_date = frappe.utils.today()

		if not self.recorded_by:
			self.recorded_by = frappe.session.user

		if not self.status:
			self.status = "Active"
