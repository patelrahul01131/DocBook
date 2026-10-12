# Copyright (c) 2026, Rahul and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class MedicineReminder(Document):
	def validate(self):
		if not self.email_address and self.patient:
			user_email = frappe.db.get_value("Patient Profile", self.patient, "user")
			if user_email:
				self.email_address = user_email

		if self.reminder_status == "Cancelled":
			self.active = 0

		# Prevent duplicate reminder creation for same medicine & scheduled datetime
		if self.is_new() and self.prescription_medicine and self.scheduled_at:
			exists = frappe.db.exists(
				"Medicine Reminder",
				{
					"prescription_medicine": self.prescription_medicine,
					"scheduled_at": self.scheduled_at,
					"reminder_status": ["!=", "Cancelled"],
				},
			)
			if exists:
				frappe.throw(_("A reminder for this medicine at this time already exists."))
