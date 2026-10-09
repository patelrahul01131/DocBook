import frappe


@frappe.whitelist(allow_guest=True)
def list_doctors():
		doctor = frappe.get_all(
			"Doctor Profile",
			fields=[
                "user",
				"full_name",
				"phone",
				"specialty",
				"qualification",
				"experience_years",
				"consultation_fee",
				"bio",
				"profile_image",
				"rating"
			]
		)
		# frappe.logger().debug("Debug message")

		# frappe.logger().info("Information message")

		# frappe.logger().warning("Warning message")

		# frappe.logger().error("Error message")

		return doctor


    
@frappe.whitelist(allow_guest=True)
def get_doctor_by_user(user_name):
    if not user_name:
        return None
    user_doc = frappe.get_doc("User", user_name)
    return frappe.get_doc("Doctor Profile", user_doc.name)