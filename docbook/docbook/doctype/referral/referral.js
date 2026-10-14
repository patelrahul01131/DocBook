// Copyright (c) 2026, Rahul and contributors
// For license information, please see license.txt

frappe.ui.form.on("Referral", {
	refresh(frm) {
		if (frm.doc.status === "Pending" && frm.doc.referred_to_doctor) {
			// No desk-side actions; lifecycle is driven through the DocBook APIs.
		}
	},
});
