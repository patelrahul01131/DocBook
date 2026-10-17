"""
Idempotent creation of DocBook custom roles, specialties, and dummy doctors.
Wired via after_migrate in hooks.py so data always exist after deploy.
"""

import frappe


ROLES = (
	"Receptionist",
	"Laboratory",
)

# Canonical specialties that match the AI booking flow synonyms
SPECIALTIES = (
	{"specialty_name": "dentist", "description": "Dental care and oral health"},
	{"specialty_name": "cardiology", "description": "Heart and cardiovascular care"},
	{"specialty_name": "dermatology", "description": "Skin, hair, and nail care"},
	{"specialty_name": "orthopedics", "description": "Bones, joints, and muscles"},
	{"specialty_name": "pediatrics", "description": "Children's health care"},
	{"specialty_name": "general physician", "description": "General medicine and primary care"},
)

# Dummy doctors — email and password is 123456789 for all
DUMMY_DOCTORS = [
	{
		"email": "dr.sharma@docbook.com",
		"full_name": "Dr. Rajesh Sharma",
		"phone": "+91 98765 43210",
		"specialty": "cardiology",
		"qualification": "MBBS, MD (Cardiology)",
		"experience_years": 15,
		"consultation_fee": 500,
		"bio": "Senior cardiologist with 15 years of experience in interventional cardiology.",
		"rating": 4.8,
	},
	{
		"email": "dr.gupta@docbook.com",
		"full_name": "Dr. Priya Gupta",
		"phone": "+91 98765 43211",
		"specialty": "dermatology",
		"qualification": "MBBS, MD (Dermatology)",
		"experience_years": 10,
		"consultation_fee": 400,
		"bio": "Dermatologist specializing in skin disorders and cosmetic dermatology.",
		"rating": 4.7,
	},
	{
		"email": "dr.verma@docbook.com",
		"full_name": "Dr. Amit Verma",
		"phone": "+91 98765 43212",
		"specialty": "orthopedics",
		"qualification": "MBBS, MS (Orthopedics)",
		"experience_years": 12,
		"consultation_fee": 600,
		"bio": "Orthopedic surgeon specializing in joint replacement and sports injuries.",
		"rating": 4.9,
	},
	{
		"email": "dr.reddy@docbook.com",
		"full_name": "Dr. Sunita Reddy",
		"phone": "+91 98765 43213",
		"specialty": "pediatrics",
		"qualification": "MBBS, MD (Pediatrics)",
		"experience_years": 8,
		"consultation_fee": 350,
		"bio": "Pediatrician with expertise in child health and vaccinations.",
		"rating": 4.6,
	},
	{
		"email": "dr.joshi@docbook.com",
		"full_name": "Dr. Vikram Joshi",
		"phone": "+91 98765 43214",
		"specialty": "general physician",
		"qualification": "MBBS",
		"experience_years": 20,
		"consultation_fee": 300,
		"bio": "General physician providing primary care and preventive medicine.",
		"rating": 4.5,
	},
	{
		"email": "dr.khan@docbook.com",
		"full_name": "Dr. Ahmed Khan",
		"phone": "+91 98765 43215",
		"specialty": "dentist",
		"qualification": "BDS, MDS",
		"experience_years": 11,
		"consultation_fee": 250,
		"bio": "Dentist specializing in oral surgery and dental implants.",
		"rating": 4.4,
	},
]

PASSWORD = "123456789"


def _set_password_ignore_policy(user, password):
	"""Set user password bypassing Frappe's password strength policy."""
	user.new_password = password
	user.flags.ignore_password_policy = True
	user.save(ignore_permissions=True)


def create_custom_roles():
	"""Create the custom DocBook roles if they do not already exist."""
	for role_name in ROLES:
		if not frappe.db.exists("Role", role_name):
			role = frappe.get_doc({
				"doctype": "Role",
				"role_name": role_name,
				"desk_access": 1,
			})
			role.insert(ignore_permissions=True)
	frappe.db.commit()


def create_specialties():
	"""Create specialty records if they do not already exist."""
	for spec in SPECIALTIES:
		if not frappe.db.exists("Specialty", spec["specialty_name"]):
			doc = frappe.get_doc({
				"doctype": "Specialty",
				"specialty_name": spec["specialty_name"],
				"description": spec["description"],
			})
			doc.insert(ignore_permissions=True)
	frappe.db.commit()


def create_dummy_doctors():
	"""Create dummy doctor users and profiles (idempotent)."""
	# Ensure Doctor role exists
	if not frappe.db.exists("Role", "Doctor"):
		doctor_role = frappe.get_doc({
			"doctype": "Role",
			"role_name": "Doctor",
			"desk_access": 1,
		})
		doctor_role.insert(ignore_permissions=True)

	for doc_data in DUMMY_DOCTORS:
		email = doc_data["email"]

		# Skip if user already exists
		if frappe.db.exists("User", email):
			continue

		# Create User
		user = frappe.get_doc({
			"doctype": "User",
			"email": email,
			"first_name": doc_data["full_name"],
			"enabled": 1,
			"user_type": "Website User",
			"send_welcome_email": 0,
			"roles": [
				{"role": "Doctor"},
			],
		})
		user.insert(ignore_permissions=True)
		_set_password_ignore_policy(user, PASSWORD)

		# Create Doctor Profile
		profile = frappe.get_doc({
			"doctype": "Doctor Profile",
			"user": email,
			"full_name": doc_data["full_name"],
			"phone": doc_data["phone"],
			"specialty": doc_data["specialty"],
			"qualification": doc_data["qualification"],
			"experience_years": doc_data["experience_years"],
			"consultation_fee": doc_data["consultation_fee"],
			"bio": doc_data["bio"],
			"is_approved": 1,
			"rating": doc_data["rating"],
		})
		profile.insert(ignore_permissions=True)

	frappe.db.commit()


def setup_all_data():
	"""Run all idempotent setup: roles, specialties, dummy doctors."""
	create_custom_roles()
	create_specialties()
	create_dummy_doctors()

	frappe.db.commit()
