# Copyright (c) 2026, Rahul and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


VALID_STATUSES = ("Pending", "Accepted", "Rejected", "Completed")


class Referral(Document):
	def validate(self):
		"""Production-grade integrity checks for a referral episode."""
		if self.referring_doctor and self.referred_to_doctor:
			if self.referring_doctor == self.referred_to_doctor:
				frappe.throw(_("A doctor cannot refer to themselves"))

		if self.source_appointment and self.target_appointment:
			if self.source_appointment == self.target_appointment:
				frappe.throw(_("Source and target appointments must be different"))

		# Both appointments must belong to the same patient.
		for appt_name in (self.source_appointment, self.target_appointment):
			if not appt_name:
				continue
			appt_patient = frappe.db.get_value("Appointment", appt_name, "patient")
			if appt_patient and self.patient and appt_patient != self.patient:
				frappe.throw(
					_("Appointment {0} does not belong to this patient").format(appt_name)
				)

		if self.status and self.status not in VALID_STATUSES:
			frappe.throw(_("Invalid referral status: {0}").format(self.status))

		if not self.referral_date:
			self.referral_date = frappe.utils.now_datetime()

	def on_update(self):
		"""Keep the linked appointments pointing back at this referral."""
		for appt_name in (self.source_appointment, self.target_appointment):
			if not appt_name:
				continue
			if frappe.db.exists("Appointment", appt_name):
				frappe.db.set_value("Appointment", appt_name, "referral", self.name)
