// src/router.js
import { createRouter, createWebHistory } from 'vue-router'
import Login from './components/Login.vue'
import Signup from './components/Signup.vue'
import FindDoctors from './components/Home.vue'
import DoctorDetail from './components/DoctorDetail.vue'
import MyAppointments from './components/MyAppointments.vue'
import DoctorDashboard from './components/DoctorDashboard.vue'
import DoctorAppointments from './components/DoctorAppointments.vue'
import DoctorProfile from './components/DoctorProfile.vue'
import ShowAppointment from './components/ShowAppointment.vue'
import Auth from './components/auth.vue'

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
  {path: '/show-appointment/:id', component: ShowAppointment}
]

export default createRouter({ history: createWebHistory(), routes })