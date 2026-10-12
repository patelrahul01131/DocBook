"""
Medicine Reminder API.

- ``get_my_reminders`` powers the patient Medicine Reminders page.
- ``process_due_reminders`` is the scheduler entry point (runs every 15
  minutes, see hooks.py) that emails patients for due reminders.
"""

import frappe
from frappe import _

MAX_RETRIES = 3


def _require_auth():
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in first"), frappe.AuthenticationError)


def _get_patient_profile(user=None):
	user = user or frappe.session.user
	return frappe.db.get_value(
		"Patient Profile",
		{"user": user},
		["name", "full_name", "user"],
		as_dict=True,
	)


# ---------------------------------------------------------------------------
# Patient views
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_my_reminders(status=None):
	"""Return medicine reminders for the authenticated patient."""
	_require_auth()

	patient = _get_patient_profile()
	if not patient:
		frappe.throw(_("Patient profile not found for this account"))

	conditions = "WHERE r.patient = %(patient)s"
	values = {"patient": patient.name}

	if status:
		conditions += " AND r.reminder_status = %(status)s"
		values["status"] = status

	reminders = frappe.db.sql(
		f"""
		SELECT
			r.name,
			r.patient,
			r.prescription,
			r.prescription_medicine,
			r.scheduled_at,
			r.reminder_status,
			r.active,
			r.email_address,
			r.sent_at,
			r.retry_count,
			r.last_error,
			pm.prescribed_medicine_name,
			pm.dosage,
			pm.frequency,
			pm.route,
			pm.instructions,
			m.medicine_name,
			m.strength,
			m.dosage_form
		FROM `tabMedicine Reminder` r
		LEFT JOIN `tabPrescription Medicine` pm ON pm.name = r.prescription_medicine
		LEFT JOIN `tabMedicine` m ON m.name = pm.medicine
		{conditions}
		ORDER BY r.scheduled_at DESC
		""",
		values,
		as_dict=True,
	)

	return reminders


@frappe.whitelist()
def get_my_reminder_stats():
	"""Return a small count summary for the authenticated patient."""
	_require_auth()

	patient = _get_patient_profile()
	if not patient:
		return {"total": 0, "pending": 0, "sent": 0, "failed": 0}

	rows = frappe.db.sql(
		"""
		SELECT reminder_status, COUNT(*) AS total
		FROM `tabMedicine Reminder`
		WHERE patient = %(patient)s
		GROUP BY reminder_status
		""",
		{"patient": patient.name},
		as_dict=True,
	)

	stats = {"total": 0, "pending": 0, "sent": 0, "failed": 0}
	for row in rows:
		stats["total"] += row.total
		key = (row.reminder_status or "").lower()
		if key in ("pending", "sent", "failed"):
			stats[key] = row.total

	return stats


# ---------------------------------------------------------------------------
# Scheduler — process due reminders
# ---------------------------------------------------------------------------

def _build_reminder_content(reminder):
	"""Return (subject, message) for a due reminder email."""
	med_name = (
		reminder.get("prescribed_medicine_name")
		or reminder.get("medicine_name")
		or "your medicine"
	)
	dosage = reminder.get("dosage") or ""
	frequency = reminder.get("frequency") or ""
	instructions = reminder.get("instructions") or ""

	subject = _("DocBook Reminder: Time to take {0}").format(med_name)

	lines = [
		_("Hi, this is a reminder from DocBook to take your medicine."),
		"",
		_("Medicine: {0}").format(med_name),
	]
	if dosage:
		lines.append(_("Dosage: {0}").format(dosage))
	if frequency:
		lines.append(_("Frequency: {0}").format(frequency))
	if instructions:
		lines.append(_("Instructions: {0}").format(instructions))
	lines.append("")
	lines.append(_("Stay healthy — DocBook"))

	message = "<br>".join(
		frappe.utils.escape_html(str(line)) for line in lines
	)

	return subject, message


@frappe.whitelist()
def process_due_reminders():
	"""
	Scheduler entry point (every 15 minutes).

	Finds all Pending, active reminders whose scheduled time has passed,
	emails the patient, and marks them Sent (or Failed after MAX_RETRIES).
	"""
	now = frappe.utils.now_datetime()

	due = frappe.db.sql(
		"""
		SELECT
			r.name,
			r.email_address,
			r.retry_count,
			r.prescription_medicine,
			r.scheduled_at,
			pm.prescribed_medicine_name,
			pm.dosage,
			pm.frequency,
			pm.instructions,
			m.medicine_name
		FROM `tabMedicine Reminder` r
		LEFT JOIN `tabPrescription Medicine` pm ON pm.name = r.prescription_medicine
		LEFT JOIN `tabMedicine` m ON m.name = pm.medicine
		WHERE r.reminder_status = 'Pending'
		  AND r.active = 1
		  AND r.scheduled_at <= %(now)s
		ORDER BY r.scheduled_at ASC
		""",
		{"now": now},
		as_dict=True,
	)

	sent = 0
	failed = 0
	skipped = 0

	for reminder in due:
		recipient = (reminder.get("email_address") or "").strip()
		if not recipient:
			# Fall back to the patient's linked user email.
			patient_name = frappe.db.get_value(
				"Medicine Reminder", reminder.name, "patient"
			)
			if patient_name:
				recipient = (
					frappe.db.get_value(
						"Patient Profile", patient_name, "user"
					)
					or ""
				).strip()

		if not recipient:
			skipped += 1
			continue

		subject, message = _build_reminder_content(reminder)

		try:
			frappe.sendmail(
				recipients=[recipient],
				subject=subject,
				message=message,
				header=[_("Medicine Reminder"), "teal"],
			)
			frappe.db.set_value(
				"Medicine Reminder",
				reminder.name,
				{
					"reminder_status": "Sent",
					"sent_at": now,
					"active": 0,
					"last_error": None,
				},
			)
			sent += 1
		except Exception as exc:  # noqa: BLE001 - broad to keep scheduler resilient
			retry = (reminder.get("retry_count") or 0) + 1
			new_status = "Failed" if retry >= MAX_RETRIES else "Pending"
			frappe.db.set_value(
				"Medicine Reminder",
				reminder.name,
				{
					"retry_count": retry,
					"reminder_status": new_status,
					"last_error": str(exc)[:500],
				},
			)
			if new_status == "Failed":
				failed += 1

	frappe.db.commit()

	return {
		"processed": len(due),
		"sent": sent,
		"failed": failed,
		"skipped": skipped,
	}
