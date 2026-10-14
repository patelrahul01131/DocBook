// src/router/router.js
import { createRouter, createWebHistory } from 'vue-router'

// Landing (public marketing page shown at "/")
import Landing from '../portals/Landing.vue'

// Auth
import Auth from '../components/auth.vue'

// Patient portal
import FindDoctors from '../portals/patient/Home.vue'
import DoctorDetail from '../portals/patient/DoctorDetail.vue'
import MyAppointments from '../portals/patient/MyAppointments.vue'
import DoctorProfile from '../portals/patient/DoctorProfile.vue'
import ShowAppointment from '../portals/patient/ShowAppointment.vue'
import PatientDashboard from '../portals/patient/PatientDashboard.vue'
import MedicalHistory from '../portals/patient/MedicalHistory.vue'
import Prescriptions from '../portals/patient/Prescriptions.vue'
import MedicineReminders from '../portals/patient/MedicineReminders.vue'
import MedicineCatalog from '../portals/patient/MedicineCatalog.vue'

// Doctor portal
import DoctorDashboard from '../portals/doctor/DoctorDashboard.vue'
import DoctorAppointments from '../portals/doctor/DoctorAppointments.vue'
import DoctorPatients from '../portals/doctor/DoctorPatients.vue'
import ConsultationForm from '../portals/doctor/ConsultationForm.vue'
import Referrals from '../portals/doctor/Referrals.vue'

// Patient reports
import Reports from '../portals/patient/Reports.vue'

// Receptionist + Laboratory portals
import QueueDashboard from '../portals/receptionist/QueueDashboard.vue'
import LabWorklist from '../portals/lab/LabWorklist.vue'

const routes = [
  { path: '/', component: Landing },

  // Auth
  { path: '/login', component: Auth },
  { path: '/signup', component: Auth },

  // Patient routes
  { path: '/home', component: FindDoctors, meta: { public: true } },
  { path: '/find-doctors', redirect: '/home' },
  { path: '/doctor/:id', component: DoctorDetail, meta: { public: true } },
  { path: '/my-appointments', component: MyAppointments, meta: { auth: true } },
  { path: '/doctor_profile', component: DoctorProfile, meta: { public: true } },
  { path: '/show-appointment/:id', component: ShowAppointment, meta: { auth: true } },
  { path: '/patient-dashboard', component: PatientDashboard, meta: { auth: true } },
  { path: '/medical-history', component: MedicalHistory, meta: { auth: true } },
  { path: '/prescriptions', component: Prescriptions, meta: { auth: true } },
  { path: '/medicine-reminders', component: MedicineReminders, meta: { auth: true } },
  { path: '/medicines', component: MedicineCatalog, meta: { auth: true } },

  // Doctor routes
  { path: '/doctor', component: DoctorDashboard, meta: { auth: true } },
  { path: '/doctor-appointments', component: DoctorAppointments, meta: { auth: true } },
  { path: '/doctor-patients', component: DoctorPatients, meta: { auth: true } },
  { path: '/consultation/:id', component: ConsultationForm, meta: { auth: true } },
  { path: '/referrals', component: Referrals, meta: { auth: true } },

  // Patient reports
  { path: '/reports', component: Reports, meta: { auth: true } },

  // Receptionist + Laboratory
  { path: '/receptionist', component: QueueDashboard, meta: { auth: true } },
  { path: '/laboratory', component: LabWorklist, meta: { auth: true } },

  // Fallback → landing
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({ history: createWebHistory(), routes })

// Routes that render WITHOUT the portal chrome (sidebar/drawer).
export const standaloneRoutes = ['/', '/login', '/signup']

export function isStandaloneRoute(path) {
  return standaloneRoutes.includes(path)
}

export default router

