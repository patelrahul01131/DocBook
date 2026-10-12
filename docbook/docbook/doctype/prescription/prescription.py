# Copyright (c) 2026, Rahul and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Prescription(Document):
	def validate(self):
		if not self.patient:
			frappe.throw(_("Patient is required"))

		if not self.doctor:
			frappe.throw(_("Doctor is required"))

		if not self.prescription_date:
			self.prescription_date = frappe.utils.today()

		if not self.status:
			self.status = "Active"

		if self.follow_up_date and self.prescription_date:
			if frappe.utils.getdate(self.follow_up_date) < frappe.utils.getdate(self.prescription_date):
				frappe.throw(_("Follow-up date cannot be earlier than prescription date"))

	def on_update(self):
		# When prescription status is set to Cancelled, cancel medicines and reminders
		if self.status == "Cancelled":
			self.cancel_linked_medicines_and_reminders()

	def cancel_linked_medicines_and_reminders(self):
		# Update prescription medicines to Cancelled
		frappe.db.sql(
			"""
			UPDATE `tabPrescription Medicine`
			SET status = 'Cancelled'
			WHERE prescription = %s AND status != 'Cancelled'
			""",
			self.name,
		)

		# Cancel pending reminders
		frappe.db.sql(
			"""
			UPDATE `tabMedicine Reminder`
			SET reminder_status = 'Cancelled', active = 0
			WHERE prescription = %s AND reminder_status = 'Pending'
			""",
			self.name,
		)
