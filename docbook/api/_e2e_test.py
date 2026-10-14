"""
End-to-end test for the Referral + Patient Report + Queue features.

Run with:
    bench --site docbook.local execute docbook.api._e2e_test.run_e2e
"""

import frappe
from frappe.utils import today, add_days


def _cleanup():
	"""Remove artifacts from prior runs so the test is repeatable."""
	for r in frappe.get_all("Patient Report", fields=["name"]):
		frappe.delete_doc("Patient Report", r.name, ignore_permissions=True, force=True)
	for r in frappe.get_all("Referral", fields=["name"]):
		frappe.delete_doc("Referral", r.name, ignore_permissions=True, force=True)
	frappe.db.sql(
		"UPDATE `tabAppointment` SET referral=NULL "
		"WHERE referral IS NOT NULL AND referral != ''"
	)
	for r in frappe.get_all("Appointment",
		filters={"reason": ["in", ["E2E_QUEUE", "Referral: E2E chest pain"]]},
		fields=["name"]):
		frappe.delete_doc("Appointment", r.name, ignore_permissions=True, force=True)
	frappe.db.commit()


def _ensure_specialist():
	if not frappe.db.exists("User", "specialist@example.com"):
		frappe.get_doc({
			"doctype": "User", "email": "specialist@example.com",
			"first_name": "Cardio", "last_name": "Spec", "enabled": 1,
			"user_type": "Website User", "send_welcome_email": 0,
		}).insert(ignore_permissions=True)
	if not frappe.db.exists("Doctor Profile", "specialist@example.com"):
		frappe.get_doc({
			"doctype": "Doctor Profile", "user": "specialist@example.com",
			"full_name": "Cardio Spec", "specialty": "Cardiology",
			"is_approved": 1, "experience_years": 8,
		}).insert(ignore_permissions=True)
	frappe.db.commit()


def _mk_appt(patient, doctor, date, time, reason="E2E_QUEUE"):
	return frappe.get_doc({
		"doctype": "Appointment", "patient": patient, "doctor": doctor,
		"appointment_date": date, "appointment_time": time,
		"status": "Confirmed", "reason": reason,
		"created_at": frappe.utils.now_datetime(),
	}).insert(ignore_permissions=True).name


def run_e2e():
	from docbook.api.referral import create_referral, get_referral, accept_referral, link_appointment_to_referral
	from docbook.api.report import order_report, upload_report, mark_report_reviewed
	from docbook.api.queue import get_queue, check_in_patient, call_next_patient, get_my_queue_position

	results = []
	def check(label, cond, extra=""):
		status = "PASS" if cond else "FAIL"
		results.append((status, label, extra))
		print(f"[{status}] {label} {extra}")

	_cleanup()
	_ensure_specialist()

	gp = "bhagyesh@gmail.com"
	spec = "specialist@example.com"
	pat = "patient1@gmail.com"
	pat2 = "bhago@gmail.com"
	t = today()

	apt_source = _mk_appt(pat, gp, t, "10:00:00")
	apt_wait = _mk_appt(pat2, gp, t, "10:30:00")

	# Test 1: create referral; target booked+linked separately (avoids calendar flakiness)
	ref = create_referral(
		source_appointment=apt_source, referred_to_doctor=spec,
		reason="E2E chest pain", clinical_notes="Evaluate cardiac murmur",
	)
	check("referral created", bool(ref.get("referral")), str(ref.get("referral")))
	ref_name = ref["referral"]

	src_doc = frappe.get_doc("Appointment", apt_source)
	check("source linked to referral", src_doc.referral == ref_name, f"got={src_doc.referral}")

	target = _mk_appt(pat, spec, add_days(t, 3), "14:00:00", reason="Referral: E2E chest pain")
	link_res = link_appointment_to_referral(target, ref_name)
	check("target appointment linked", link_res.get("success") is True, str(link_res))
	tgt_doc = frappe.get_doc("Appointment", target)
	check("target linked to referral", tgt_doc.referral == ref_name, f"got={tgt_doc.referral}")
	ref_after = frappe.get_doc("Referral", ref_name)
	check("referral.target_appointment recorded", ref_after.target_appointment == target,
		f"got={ref_after.target_appointment}")

	# Test 2: order a report on the source appointment
	rep = order_report(appointment=apt_source, report_type="Lab",
		title="E2E Blood Test", description="CBC panel", laboratory="Core Lab")
	check("report ordered", rep.get("status") == "Ordered", str(rep.get("report")))
	rep_name = rep["report"]
	src_doc.reload()
	check("visit_stage -> Report Pending", src_doc.visit_stage == "Report Pending",
		f"got={src_doc.visit_stage}")

	# Test 3: upload the report -> queue-skip
	up = upload_report(report=rep_name, file_url="/files/e2e_report.pdf", findings="All normal")
	check("report uploaded", up.get("status") == "Uploaded", str(up.get("status")))
	src_doc.reload()
	check("visit_stage -> Ready For Review", src_doc.visit_stage == "Ready For Review",
		f"got={src_doc.visit_stage}")
	check("priority set (skip queue)", int(src_doc.priority or 0) == 1, f"p={src_doc.priority}")
	check("auto checked-in on report return", int(src_doc.checked_in or 0) == 1)

	# Test 4: referral detail shows both appointments + the report
	detail = get_referral(ref_name)
	check("referral has 2 appointments", len(detail.get("appointments", [])) == 2,
		f"n={len(detail.get('appointments', []))}")
	check("referral shares the report", len(detail.get("reports", [])) >= 1,
		f"n={len(detail.get('reports', []))}")

	# Test 5: queue ordering -> Ready For Review ranks before Waiting
	check_in_patient(apt_wait)
	q = get_queue(doctor=gp, date=t)
	order_names = [r["name"] for r in q["queue"]]
	check("ready-for-review ahead of waiting",
		order_names.index(apt_source) < order_names.index(apt_wait),
		f"order={order_names}")

	# Test 6: call_next picks the return visit first
	nxt = call_next_patient(doctor=gp)
	serving = (nxt.get("now_serving") or {}).get("name")
	check("call_next picks return visit", serving == apt_source, f"now_serving={serving}")

	# Test 7: specialist accepts the referral (authz)
	frappe.set_user(spec)
	try:
		acc = accept_referral(ref_name)
		check("specialist accepts referral", acc.get("status") == "Accepted", str(acc.get("status")))
	finally:
		frappe.set_user("Administrator")

	# Test 8: patient queue position endpoint (as the patient)
	frappe.set_user(pat)
	try:
		pos = get_my_queue_position(appointment=apt_source)
	finally:
		frappe.set_user("Administrator")
	check("patient queue position",
		pos.get("found") is True
		and pos.get("visit_stage") in ("Ready For Review", "In Consultation"),
		f"stage={pos.get('visit_stage')}")

	# Test 9: doctor report review
	frappe.set_user(gp)
	try:
		rv = mark_report_reviewed(rep_name)
		check("report reviewed", rv.get("status") == "Reviewed", str(rv.get("status")))
	finally:
		frappe.set_user("Administrator")

	frappe.db.commit()
	passed = sum(1 for s, _, _ in results if s == "PASS")
	failed = sum(1 for s, _, _ in results if s == "FAIL")
	print(f"\n=== E2E SUMMARY: {passed} passed, {failed} failed ===")
	return {"passed": passed, "failed": failed, "results": results}
