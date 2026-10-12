# Copyright (c) 2026, Rahul and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class PrescriptionMedicine(Document):
	def validate(self):
		if not self.prescription:
			frappe.throw(_("Prescription is required"))

		if not self.medicine:
			frappe.throw(_("Medicine is required"))

		if not self.patient:
			frappe.throw(_("Patient is required"))

		if not self.doctor:
			frappe.throw(_("Doctor is required"))

		if not self.start_date:
			frappe.throw(_("Start date is required"))

		if not self.end_date:
			frappe.throw(_("End date is required"))

		if frappe.utils.getdate(self.end_date) < frappe.utils.getdate(self.start_date):
			frappe.throw(_("End date cannot be earlier than start date"))

		# Validate the linked medicine is active
		if self.medicine and self.status == "Active":
			is_active = frappe.db.get_value("Medicine", self.medicine, "is_active")
			if not is_active:
				frappe.throw(_(f"Medicine '{self.medicine}' is not active and cannot be prescribed."))

		# Populate prescribed_medicine_name from the Medicine catalog
		if self.medicine and not self.prescribed_medicine_name:
			med = frappe.db.get_value(
				"Medicine",
				self.medicine,
				["medicine_name", "generic_name", "strength", "dosage_form"],
				as_dict=True,
			)
			if med:
				parts = [med.medicine_name]
				if med.strength:
					parts.append(med.strength)
				if med.dosage_form:
					parts.append(f"({med.dosage_form})")
				self.prescribed_medicine_name = " ".join(parts)

		# Validate dose times against frequency
		self._validate_dose_times()

	def _validate_dose_times(self):
		freq = self.frequency or ""
		times = [
			self.dose_time_1,
			self.dose_time_2,
			self.dose_time_3,
			self.dose_time_4,
		]
		filled = [t for t in times if t]

		freq_map = {
			"Once Daily": 1,
			"Twice Daily": 2,
			"Three Times Daily": 3,
			"Four Times Daily": 4,
		}

		if freq in freq_map:
			expected = freq_map[freq]
			if len(filled) > expected:
				frappe.msgprint(
					_(f"Note: {freq} typically requires {expected} dose time(s), but {len(filled)} were provided.")
				)

	def on_update(self):
		# When medicine is cancelled, cancel its pending reminders
		if self.status == "Cancelled":
			frappe.db.sql(
				"""
				UPDATE `tabMedicine Reminder`
				SET reminder_status = 'Cancelled', active = 0
				WHERE prescription_medicine = %s AND reminder_status = 'Pending'
				""",
				self.name,
			)
