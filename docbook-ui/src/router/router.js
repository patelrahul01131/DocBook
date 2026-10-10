// src/router.js
import { createRouter, createWebHistory } from 'vue-router'
import FindDoctors from '../portals/patient/Home.vue'
import DoctorDetail from '../portals/patient/DoctorDetail.vue'
import MyAppointments from '../portals/patient/MyAppointments.vue'
import DoctorDashboard from '../portals/doctor/DoctorDashboard.vue'
import DoctorAppointments from '../portals/doctor/DoctorAppointments.vue'
import DoctorProfile from '../portals/patient/DoctorProfile.vue'
import ShowAppointment from '../portals/patient/ShowAppointment.vue'
import PatientDashboard from '../portals/patient/PatientDashboard.vue'
import DoctorProfileBooking from '../portals/patient/DoctorProfileBooking.vue'
import Auth from '../components/auth.vue'

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', component: Auth },
  { path: '/signup', component: Auth },
  { path: '/home', component: FindDoctors },
  { path: '/doctor/:id', component: DoctorDetail },
  { path: '/my-appointments', component: MyAppointments },
  { path: '/doctor', component: DoctorDashboard },
  { path: '/doctor-appointments', component: DoctorAppointments },
  {path: '/doctor_profile', component: DoctorProfile},
  {path: '/show-appointment/:id', component: ShowAppointment},
  {path: '/patient-dashboard', component: PatientDashboard},
  {path: '/doctor-profile-booking', component: DoctorProfileBooking}
]

export default createRouter({ history: createWebHistory(), routes })