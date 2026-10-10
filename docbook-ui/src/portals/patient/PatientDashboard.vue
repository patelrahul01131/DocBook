
<script setup>
import { computed, onMounted, ref } from 'vue'
import { Badge, Button } from 'frappe-ui'
import { useRouter } from 'vue-router'
import { call } from '../../api'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const appointments = ref([])
const doctors = ref([])
const searchQuery = ref('')
const loading = ref(true)
const refreshing = ref(false)
const error = ref('')

// --------------------------------------------------
// Authenticated patient
// --------------------------------------------------

const patientEmail = computed(() => {
  const user = auth.user || auth.currentUser || null

  return String(
    user?.email ||
    user?.name ||
    ''
  ).trim().toLowerCase()
})

const patientName = computed(() => {
  const user = auth.user || auth.currentUser || null
  const fullName = user?.full_name || user?.fullname

  if (fullName) return fullName.split(' ')[0]

  const email = patientEmail.value
  return email ? email.split('@')[0] : 'there'
})

// --------------------------------------------------
// Fetch existing APIs
// --------------------------------------------------

async function fetchDashboard(isRefresh = false) {
  if (isRefresh) {
    refreshing.value = true
  } else {
    loading.value = true
  }

  error.value = ''

  try {
    if (!patientEmail.value) {
      throw new Error('Please sign in to view your dashboard.')
    }

    const [appointmentResult, doctorResult] = await Promise.all([
      call('docbook.api.appointment.list_appointment',{
        patient: auth.user.email
      }),
      call('docbook.api.doctor.list_doctors').catch((err) => {
        console.error('Could not load doctor directory:', err)
        return []
      }),
    ])

    const appointmentRows = Array.isArray(appointmentResult)
      ? appointmentResult
      : appointmentResult?.data ||
        appointmentResult?.message ||
        []

    // Display only records belonging to the signed-in patient.
    // The server must independently enforce this restriction.
    appointments.value = appointmentRows.filter((appointment) => {
      const owner = String(
        appointment.patient_email ||
        appointment.patient ||
        ''
      ).trim().toLowerCase()

      return owner && owner === patientEmail.value
    })

    doctors.value = Array.isArray(doctorResult)
      ? doctorResult
      : doctorResult?.data || doctorResult?.message || []
  } catch (err) {
    console.error('Patient dashboard error:', err)
    error.value = err.message ||
      'Unable to load your dashboard. Please try again.'
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

// --------------------------------------------------
// Appointment helpers
// --------------------------------------------------

function appointmentDateTime(appointment) {
  const date = appointment.appointment_date || appointment.date
  const time = appointment.appointment_time || appointment.time || '00:00:00'

  if (!date) return null

  const parsed = new Date(`${date}T${time}`)

  return Number.isNaN(parsed.getTime()) ? null : parsed
}

function formatDate(appointment) {
  const date = appointmentDateTime(appointment)

  if (!date) return 'Date not available'

  return new Intl.DateTimeFormat('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(date)
}

function formatTime(appointment) {
  const date = appointmentDateTime(appointment)

  if (!date) return 'Time not available'

  return new Intl.DateTimeFormat('en-IN', {
    hour: 'numeric',
    minute: '2-digit',
  }).format(date)
}

function formatFee(fee) {
  if (fee == null || fee === '') return 'Not specified'

  const amount = Number(fee)

  if (!Number.isFinite(amount)) return 'Not specified'

  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(amount)
}

function statusOf(appointment) {
  return String(
    appointment.status || 'Pending'
  ).trim().toLowerCase()
}

function isCompleted(appointment) {
  return ['completed', 'resolved'].includes(statusOf(appointment))
}

function isCancelled(appointment) {
  return ['cancelled', 'canceled'].includes(statusOf(appointment))
}

function isUpcoming(appointment) {
  const date = appointmentDateTime(appointment)

  return Boolean(
    date &&
    date >= new Date() &&
    !isCompleted(appointment) &&
    !isCancelled(appointment)
  )
}

function doctorName(appointment) {
  const doctorId = appointment.doctor

  const doctor = doctors.value.find((item) =>
    item.user === doctorId ||
    item.name === doctorId
  )

  return (
    appointment.doctor_name ||
    doctor?.full_name ||
    doctor?.doctor_name ||
    doctor?.name ||
    doctorId ||
    'Doctor'
  )
}

function doctorSpecialty(appointment) {
  const doctor = doctors.value.find((item) =>
    item.user === appointment.doctor ||
    item.name === appointment.doctor
  )

  return appointment.specialty || doctor?.specialty || 'Healthcare professional'
}

// --------------------------------------------------
// Dashboard statistics
// --------------------------------------------------

const upcomingAppointments = computed(() =>
  appointments.value
    .filter(isUpcoming)
    .sort((a, b) =>
      appointmentDateTime(a) - appointmentDateTime(b)
    )
)

const nextAppointments = computed(() =>
  upcomingAppointments.value.slice(0, 3)
)

const pendingAppointments = computed(() =>
  appointments.value.filter((appointment) =>
    ['pending', 'booked', 'confirmed'].includes(statusOf(appointment))
  ).length
)

const completedAppointments = computed(() =>
  appointments.value.filter(isCompleted).length
)

const filteredDoctors = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()

  if (!query) return doctors.value.slice(0, 3)

  return doctors.value
    .filter((doctor) =>
      [
        doctor.full_name,
        doctor.doctor_name,
        doctor.specialty,
        doctor.qualification,
      ].some((value) =>
        String(value || '').toLowerCase().includes(query)
      )
    )
    .slice(0, 3)
})

function viewDoctor(doctor) {
  const identifier = doctor.user || doctor.name

  if (!identifier) return

  router.push({
    path: '/doctor_profile',
    query: { doctor: identifier },
  })
}

function findDoctors() {
  router.push('/find-doctors')
}

function viewAppointments(slot_name) {
  router.push(`/show-appointment/${slot_name}`)
}

onMounted(() => {
  fetchDashboard()
})
</script>

<template>
  <main class="patient-dashboard">
    <div class="dashboard-shell">

      <!-- Welcome -->
      <header class="welcome-header">
        <div class="welcome-copy">
          <div class="eyebrow">
            <span class="lucide-heart-pulse"></span>
            DOCBOOK PATIENT PORTAL
          </div>

          <h1>
            Hello, {{ patientName }}<span></span>
          </h1>

          <p>
            Your health journey, appointments, and care —
            all in one place.
          </p>
        </div>

        <div class="welcome-actions">
          <Button
            label="Find a doctor"
            icon-left="lucide-search"
            @click="findDoctors"
          />

          <Button
            label="Refresh"
            icon-left="lucide-refresh-cw"
            :loading="refreshing"
            :disabled="loading || refreshing"
            @click="fetchDashboard(true)"
          />
        </div>
      </header>

      <!-- Error -->
      <section v-if="error" class="error-panel">
        <span class="lucide-circle-alert"></span>

        <div class="error-copy">
          <strong>Unable to load your dashboard</strong>
          <p>{{ error }}</p>
        </div>

        <Button
          label="Try again"
          @click="fetchDashboard()"
        />
      </section>

      <template v-else>

        <!-- Statistics -->
        <section class="stats-grid">
          <article class="stat-card">
            <div class="stat-icon blue">
              <span class="lucide-calendar-days"></span>
            </div>

            <p>Total appointments</p>

            <h2>{{ loading ? '—' : appointments.length }}</h2>

            <span class="stat-caption">
              Your appointment records
            </span>
          </article>

          <article class="stat-card">
            <div class="stat-icon teal">
              <span class="lucide-calendar-check"></span>
            </div>

            <p>Upcoming visits</p>

            <h2>{{ loading ? '—' : upcomingAppointments.length }}</h2>

            <span class="stat-caption">
              Scheduled for now or later
            </span>
          </article>

          <article class="stat-card">
            <div class="stat-icon amber">
              <span class="lucide-clock-3"></span>
            </div>

            <p>Pending bookings</p>

            <h2>{{ loading ? '—' : pendingAppointments }}</h2>

            <span class="stat-caption">
              Awaiting the next step
            </span>
          </article>

          <article class="stat-card">
            <div class="stat-icon purple">
              <span class="lucide-check-circle-2"></span>
            </div>

            <p>Completed visits</p>

            <h2>{{ loading ? '—' : completedAppointments }}</h2>

            <span class="stat-caption">
              Completed appointments
            </span>
          </article>
        </section>

        <!-- Upcoming appointments -->
        <section class="section-block">
          <div class="section-heading">
            <div>
              <div class="eyebrow">YOUR HEALTH SCHEDULE</div>
              <h2>Upcoming appointments</h2>
              <p>Keep track of your next visits.</p>
            </div>

            <button
              class="text-action"
              type="button"
              @click="viewAppointments"
            >
              View all
              <span class="lucide-arrow-up-right"></span>
            </button>
          </div>

          <!-- Loading -->
          <div v-if="loading" class="appointment-grid">
            <div
              v-for="item in 3"
              :key="item"
              class="appointment-card skeleton-card"
            >
              <div class="skeleton skeleton-line"></div>
              <div class="skeleton skeleton-line wide"></div>
              <div class="skeleton skeleton-block"></div>
            </div>
          </div>

          <!-- Empty state -->
          <div
            v-else-if="!upcomingAppointments.length"
            class="empty-panel"
          >
            <div class="empty-icon">
              <span class="lucide-calendar-plus"></span>
            </div>

            <h3>No upcoming appointments</h3>

            <p>
              When you book your next visit, its details will
              appear here.
            </p>

            <Button
              label="Find a doctor"
              icon-left="lucide-search"
              @click="findDoctors"
            />
          </div>

          <!-- Appointment cards -->
          <div v-else class="appointment-grid">
            <article
              v-for="appointment in nextAppointments"
              :key="appointment.name"
              class="appointment-card"
            >
              <div class="appointment-top">
                <div class="appointment-icon">
                  <span class="lucide-stethoscope"></span>
                </div>

                <Badge
                  :theme="
                    statusOf(appointment) === 'confirmed'
                      ? 'green'
                      : statusOf(appointment) === 'pending'
                        ? 'orange'
                        : 'blue'
                  "
                >
                  {{ appointment.status || 'Pending' }}
                </Badge>
              </div>

              <h3>{{ doctorName(appointment) }}</h3>

              <p class="doctor-specialty">
                {{ doctorSpecialty(appointment) }}
              </p>

              <div class="appointment-meta">
                <div>
                  <span class="lucide-calendar-days"></span>
                  {{ formatDate(appointment) }}
                </div>

                <div>
                  <span class="lucide-clock-3"></span>
                  {{ formatTime(appointment) }}
                </div>
              </div>

              <div class="appointment-footer">
                <div class="fee-info">
                  <span>Consultation fee</span>
                  <strong>{{ formatFee(appointment.fee) }}</strong>
                </div>

                <Button
                  label="Details"
                  icon-right="lucide-arrow-up-right"
                  @click="viewAppointments(appointment.slot)"
                />
              </div>
            </article>
          </div>
        </section>

        <!-- Find a doctor -->
        <section class="section-block doctor-section">
          <div class="section-heading">
            <div>
              <div class="eyebrow">PERSONALIZED CARE</div>
              <h2>Discover doctors</h2>
              <p>Explore available healthcare professionals.</p>
            </div>

            <button
              class="text-action"
              type="button"
              @click="findDoctors"
            >
              Explore all
              <span class="lucide-arrow-up-right"></span>
            </button>
          </div>

          <div class="doctor-search">
            <span class="lucide-search"></span>

            <Input
              v-model="searchQuery"
              placeholder="Search by doctor or specialty..."
            />
          </div>

          <div v-if="loading" class="doctor-grid">
            <div
              v-for="item in 3"
              :key="item"
              class="doctor-card skeleton-card"
            >
              <div class="skeleton skeleton-avatar"></div>
              <div class="skeleton skeleton-line wide"></div>
              <div class="skeleton skeleton-line"></div>
            </div>
          </div>

          <div
            v-else-if="!filteredDoctors.length"
            class="empty-panel compact-empty"
          >
            <span class="lucide-search"></span>
            <h3>No doctors found</h3>
            <p>Try a different search or explore the full directory.</p>
            <Button
              label="Browse doctors"
              @click="findDoctors"
            />
          </div>

          <div v-else class="doctor-grid">
            <article
              v-for="doctor in filteredDoctors"
              :key="doctor.name || doctor.user"
              class="doctor-card"
            >
              <div class="doctor-avatar">
                <span class="lucide-user-round"></span>
              </div>

              <div class="doctor-info">
                <h3>
                  {{
                    doctor.full_name ||
                    doctor.doctor_name ||
                    doctor.name
                  }}
                </h3>

                <p>
                  {{ doctor.specialty || 'General practice' }}
                </p>

                <span class="qualification">
                  {{ doctor.qualification || 'Qualification not specified' }}
                </span>
              </div>

              <Button
                label="View profile"
                icon-right="lucide-arrow-up-right"
                @click="viewDoctor(doctor)"
              />
            </article>
          </div>
        </section>

        <!-- CTA -->
        <section class="health-banner">
          <div class="banner-icon">
            <span class="lucide-heart-pulse"></span>
          </div>

          <div class="banner-copy">
            <h2>Your health deserves attention.</h2>
            <p>
              Find the right healthcare professional for your
              next appointment with DocBook.
            </p>
          </div>

          <Button
            label="Book an appointment"
            icon-right="lucide-arrow-right"
            @click="findDoctors"
          />
        </section>
      </template>

      <footer class="dashboard-footer">
        <span>DocBook · Healthcare made simple</span>
        <button type="button" @click="viewAppointments">
          My appointments
        </button>
      </footer>
    </div>
  </main>
</template>

<style scoped>
.patient-dashboard {
  --blue: #2563eb;
  --teal: #0d9488;
  --ink: #0f172a;
  --muted: #64748b;
  --border: #e2e8f0;

  min-height: 100%;
  padding: 34px 24px;
  color: var(--ink);
  background:
    radial-gradient(ellipse at 0% 0%, rgba(37,99,235,.08), transparent 35%),
    radial-gradient(ellipse at 100% 50%, rgba(20,184,166,.07), transparent 30%),
    #f4f7fb;
}

.dashboard-shell {
  width: 100%;
  max-width: 1320px;
  margin: 0 auto;
}

.welcome-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 24px;
  margin-bottom: 30px;
}

.eyebrow {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--blue);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 1.4px;
}

.welcome-copy h1 {
  margin: 12px 0 8px;
  font-size: clamp(32px, 4vw, 46px);
  font-weight: 800;
  letter-spacing: -1.8px;
}

.welcome-copy h1 span {
  color: var(--teal);
}

.welcome-copy > p,
.section-heading p {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.7;
}

.welcome-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 42px;
}

.stat-card,
.appointment-card,
.doctor-card {
  min-width: 0;
  border: 1px solid rgba(255,255,255,.95);
  border-radius: 22px;
  background: rgba(255,255,255,.82);
  box-shadow: 0 12px 32px rgba(15,23,42,.045);
  backdrop-filter: blur(18px);
}

.stat-card {
  padding: 21px;
}

.stat-icon,
.appointment-icon,
.empty-icon,
.banner-icon {
  display: grid;
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  place-items: center;
  border-radius: 14px;
  font-size: 19px;
}

.stat-icon.blue {
  color: #2563eb;
  background: #eff6ff;
}

.stat-icon.teal {
  color: #0f766e;
  background: #ccfbf1;
}

.stat-icon.amber {
  color: #b45309;
  background: #fef3c7;
}

.stat-icon.purple {
  color: #7c3aed;
  background: #f3e8ff;
}

.stat-card > p {
  margin: 18px 0 5px;
  color: var(--muted);
  font-size: 12px;
}

.stat-card h2 {
  margin: 0;
  font-size: 31px;
  font-weight: 800;
  letter-spacing: -1px;
}

.stat-caption {
  display: block;
  margin-top: 8px;
  color: #94a3b8;
  font-size: 10px;
  line-height: 1.5;
}

.section-block {
  margin-top: 38px;
}

.section-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 18px;
  margin-bottom: 21px;
}

.section-heading h2 {
  margin: 8px 0 5px;
  font-size: 24px;
  font-weight: 780;
  letter-spacing: -.7px;
}

.text-action {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 0;
  border: 0;
  background: transparent;
  color: var(--blue);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.appointment-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 17px;
}

.appointment-card {
  display: flex;
  flex-direction: column;
  padding: 21px;
  transition: transform .2s ease, box-shadow .2s ease;
}

.appointment-card:hover,
.doctor-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 20px 40px rgba(15,23,42,.075);
}

.appointment-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 18px;
}

.appointment-icon {
  color: var(--blue);
  background: linear-gradient(135deg,#eff6ff,#ccfbf1);
}

.appointment-card h3 {
  overflow-wrap: anywhere;
  margin: 0;
  font-size: 16px;
  font-weight: 750;
}

.doctor-specialty {
  margin: 6px 0 17px;
  color: var(--muted);
  font-size: 12px;
}

.appointment-meta {
  display: grid;
  gap: 11px;
  padding: 15px 0;
  border-top: 1px solid #f1f5f9;
  border-bottom: 1px solid #f1f5f9;
}

.appointment-meta div {
  display: flex;
  align-items: center;
  gap: 9px;
  color: #475569;
  font-size: 12px;
}

.appointment-meta span {
  color: var(--teal);
}

.appointment-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-top: auto;
  padding-top: 17px;
}

.fee-info {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}

.fee-info span {
  color: #94a3b8;
  font-size: 10px;
}

.fee-info strong {
  overflow-wrap: anywhere;
  font-size: 14px;
}

.doctor-search {
  display: flex;
  align-items: center;
  gap: 10px;
  max-width: 530px;
  margin-bottom: 18px;
  padding: 5px 12px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: rgba(255,255,255,.9);
  color: #94a3b8;
}

.doctor-search > span {
  flex-shrink: 0;
}

.doctor-search :deep(input) {
  min-width: 0;
  border: 0;
  box-shadow: none;
}

.doctor-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.doctor-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 15px;
  padding: 20px;
  transition: transform .2s ease, box-shadow .2s ease;
}

.doctor-avatar {
  display: grid;
  width: 52px;
  height: 52px;
  place-items: center;
  border: 1px solid #dbeafe;
  border-radius: 16px;
  background: linear-gradient(135deg,#eff6ff,#ccfbf1);
  color: var(--blue);
  font-size: 22px;
}

.doctor-info {
  flex: 1;
  min-width: 0;
}

.doctor-info h3 {
  overflow-wrap: anywhere;
  margin: 0;
  font-size: 15px;
  font-weight: 750;
}

.doctor-info p {
  margin: 6px 0;
  color: var(--teal);
  font-size: 12px;
}

.qualification {
  display: block;
  color: var(--muted);
  font-size: 11px;
  line-height: 1.5;
}

.doctor-card > :last-child {
  width: 100%;
}

.empty-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 45px 20px;
  border: 1px dashed #cbd5e1;
  border-radius: 22px;
  background: rgba(255,255,255,.65);
  text-align: center;
}

.empty-icon {
  width: 54px;
  height: 54px;
  color: var(--blue);
  background: #eff6ff;
  font-size: 23px;
}

.empty-panel h3 {
  margin: 17px 0 7px;
  font-size: 16px;
}

.empty-panel p {
  max-width: 390px;
  margin: 0 0 20px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.7;
}

.compact-empty {
  padding: 32px 20px;
}

.error-panel {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 20px;
  border: 1px solid #fecaca;
  border-radius: 18px;
  background: #fffafa;
  color: #dc2626;
}

.error-copy {
  flex: 1;
  min-width: 0;
}

.error-copy strong {
  font-size: 13px;
}

.error-copy p {
  margin: 5px 0 0;
  color: #7f1d1d;
  font-size: 12px;
}

.health-banner {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-top: 42px;
  padding: 26px;
  border-radius: 25px;
  background: linear-gradient(125deg,#0f172a,#172554 65%,#134e4a);
  color: white;
  box-shadow: 0 22px 48px rgba(15,23,42,.13);
}

.banner-icon {
  width: 52px;
  height: 52px;
  background: rgba(255,255,255,.1);
  color: #5eead4;
  font-size: 23px;
}

.banner-copy {
  flex: 1;
  min-width: 0;
}

.banner-copy h2 {
  margin: 0 0 7px;
  font-size: 18px;
}

.banner-copy p {
  max-width: 570px;
  margin: 0;
  color: #cbd5e1;
  font-size: 12px;
  line-height: 1.7;
}

.dashboard-footer {
  display: flex;
  justify-content: space-between;
  gap: 15px;
  margin-top: 25px;
  padding-top: 19px;
  border-top: 1px solid var(--border);
  color: #94a3b8;
  font-size: 11px;
}

.dashboard-footer button {
  border: 0;
  background: transparent;
  color: var(--blue);
  cursor: pointer;
}

.skeleton {
  border-radius: 9px;
  background: linear-gradient(90deg,#f1f5f9,#e2e8f0,#f1f5f9);
  background-size: 200% 100%;
  animation: shimmer 1.5s linear infinite;
}

.skeleton-card {
  gap: 15px;
}

.skeleton-line {
  width: 60%;
  height: 13px;
}

.skeleton-line.wide {
  width: 85%;
  height: 18px;
}

.skeleton-block {
  width: 100%;
  height: 70px;
}

.skeleton-avatar {
  width: 52px;
  height: 52px;
  border-radius: 16px;
}

@keyframes shimmer {
  to { background-position: -200% 0; }
}

@media (max-width: 1050px) {
  .stats-grid {
    grid-template-columns: repeat(2,minmax(0,1fr));
  }

  .appointment-grid,
  .doctor-grid {
    grid-template-columns: repeat(2,minmax(0,1fr));
  }

  .welcome-header {
    align-items: flex-start;
    flex-direction: column;
  }
}

@media (max-width: 650px) {
  .patient-dashboard {
    padding: 23px 15px;
  }

  .welcome-copy h1 {
    font-size: 34px;
  }

  .welcome-actions {
    width: 100%;
  }

  .stats-grid {
    gap: 12px;
  }

  .stat-card {
    padding: 16px;
  }

  .appointment-grid,
  .doctor-grid {
    grid-template-columns: 1fr;
  }

  .section-heading {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }

  .health-banner {
    align-items: flex-start;
    flex-wrap: wrap;
    padding: 21px;
  }

  .banner-copy {
    flex-basis: calc(100% - 75px);
  }

  .health-banner > :last-child {
    width: 100%;
  }

  .error-panel {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .dashboard-footer {
    flex-direction: column;
  }
}

@media (max-width: 380px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .welcome-copy h1 {
    font-size: 29px;
  }

  .appointment-footer {
    align-items: flex-start;
    flex-direction: column;
  }
}

@media (prefers-reduced-motion: reduce) {
  .skeleton {
    animation: none;
  }

  .appointment-card,
  .doctor-card {
    transition: none;
  }
}
</style>