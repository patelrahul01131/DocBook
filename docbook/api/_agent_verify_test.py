import frappe
from datetime import timedelta


def run():
    results = []

    def check(label, cond, detail=""):
        results.append((label, bool(cond), detail))
        print(f"[{'PASS' if cond else 'FAIL'}] {label}  {detail}")

    # ---------------------------------------------------------------
    # 1. Doctor-name resolution (transcript: "issue locating Dr. Bhagyesh")
    # ---------------------------------------------------------------
    from docbook.api.appointment import _get_doctor_name
    for probe in ("Dr. Bhagyesh", "bhagyesh", "Bhagyesh", "BHAGYESH"):
        try:
            got = _get_doctor_name(probe)
        except Exception as e:
            got = f"ERR:{e}"
        check(f"resolve {probe!r}", got == "bhagyesh@gmail.com", str(got))

    # ---------------------------------------------------------------
    # 2. Time normalization (transcript: "10 am", "2pm")
    # ---------------------------------------------------------------
    from docbook.api import agent
    for raw, want in (("10 am", "10:00:00"), ("2pm", "14:00:00"),
                      ("2 PM", "14:00:00"), ("14:30", "14:30:00")):
        got = agent._normalize_time(raw)
        check(f"norm {raw!r} -> {want}", got == want, got)

    # ---------------------------------------------------------------
    # 3. Verifier: an UNGROUNDED "is now confirmed" must be rewritten
    #    (transcript: confirmed but never saved)
    # ---------------------------------------------------------------
    lie = ("Your appointment with Dr. Bhagyesh (Dentist) is now confirmed: "
           "Date: 2026-10-15 Time: 10:00 AM. Please arrive 10 minutes early.")
    out_lie = agent._verify_booking_reply(lie, [
        {"role": "assistant", "content": lie}])
    check("ungrounded lie rewritten",
          "haven't made" in out_lie.lower(), out_lie[:90])

    # A GROUNDED booking (tool returned success + id) is kept + stamped
    out_ok = agent._verify_booking_reply("Your appointment is now confirmed.", [
        {"role": "assistant", "content": "", "tool_calls": [
            {"id": "1", "function": {"name": "book_appointment", "arguments": "{}"}}]},
        {"role": "tool", "name": "book_appointment",
         "content": '{"success": true, "appointment_id": "APT-00029"}'},
    ])
    check("grounded booking kept + reference id",
          "APT-00029" in out_ok, out_ok[:90])

    # ---------------------------------------------------------------
    # 4. REAL booking through the tool, then prove it persisted + lists
    # ---------------------------------------------------------------
    class P:
        pass
    p = P()
    p.name = "patient1@gmail.com"
    p.user = "patient1@gmail.com"
    p.full_name = "Patient 1"

    future = (frappe.utils.getdate() + timedelta(days=3)).strftime("%Y-%m-%d")
    res = agent._t_book_appointment(p, {
        "doctor": "Dr. Bhagyesh",
        "appointment_date": future,
        "appointment_time": "10:00",
        "reason": "Dental check-up",
        "symptoms": "Pain in teeth",
    })
    check("book tool success", res.get("success") is True, str(res)[:180])
    aid = res.get("appointment_id")

    row = (frappe.db.get_value("Appointment", aid,
           ["name", "status", "appointment_date", "appointment_time", "doctor"],
           as_dict=True) if aid else None)
    check("appointment really persisted",
          bool(row) and row.status in ("Pending", "Confirmed"), str(row))

    from docbook.api.appointment import list_appointment
    lst = list_appointment(patient=p.user) or []
    ids = [a.get("name") for a in lst]
    check("new appointment appears in list", aid in ids,
          f"count={len(lst)}")

    # ---------------------------------------------------------------
    # 5. Idempotency: booking the SAME slot again must NOT duplicate
    # ---------------------------------------------------------------
    before = len([a for a in lst if a.get("name")])
    res2 = agent._t_book_appointment(p, {
        "doctor": "Dr. Bhagyesh",
        "appointment_date": future,
        "appointment_time": "10:00",
    })
    check("duplicate booking returns already_booked",
          res2.get("success") is True and res2.get("already_booked") is True
          and res2.get("appointment_id") == aid, str(res2)[:120])

    # ---------------------------------------------------------------
    # cleanup
    # ---------------------------------------------------------------
    if aid:
        slot = frappe.db.get_value("Appointment", aid, "slot")
        frappe.db.set_value("Appointment", aid, "status", "Cancelled")
        if slot:
            frappe.db.set_value("Availability Slot", slot, "is_booked", 0)
    frappe.db.commit()

    fails = [r for r in results if not r[1]]
    print("\n=== SUMMARY ===")
    print(f"{len(results) - len(fails)}/{len(results)} passed")
    for r in fails:
        print("  FAIL:", r[0], "::", r[2])
    return results
