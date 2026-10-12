<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Badge, Button } from 'frappe-ui'
import { call } from '../../api'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const loading = ref(true)
const refreshing = ref(false)
const error = ref('')

const doctor = ref(null)
const stats = ref({
  total: 0, pending: 0, confirmed: 0, completed: 0,
  cancelled: 0, today: 0, upcoming: 0, earnings: 0,
})
const todayAppointments = ref([])
const upcomingAppointments = ref([])
const recentPatients = ref([])
const uniquePatients = ref(0)

// ---------------------------------------------------------------
// Derived values
// ---------------------------------------------------------------

const doctorName = computed(() => {
  const user = auth.user || {}
  return (
    doctor.value?.full_name ||
    user.full_name ||
    (user.email ? user.email.split('@')[0] : 'Doctor')
  )
})

const firstName = computed(() => {
  const parts = String(doctorName.value).trim().split(/\s+/)
  const clean = parts.filter((p) => !/^dr\.?$/i.test(p))
  return (clean[0] || parts[0] || 'Doctor').replace(/\.$/, '')
})

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
})

const doctorInitials = computed(() => {
  const name = doctorName.value.replace(/^dr\.?\s+/i, '')
  const parts = name.split(/\s+/).filter(Boolean)
  if (!parts.length) return 'DR'
  return parts.map((p) => p[0]).join('').slice(0, 2).toUpperCase()
})

const todayLabel = computed(() =>
  new Date().toLocaleDateString('en-IN', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  })
)

const formattedEarnings = computed(() => {
  const n = Number(stats.value.earnings || 0)
  if (!n) return '₹0'
  return `₹${n.toLocaleString('en-IN')}`
})

// ---------------------------------------------------------------
// Data
// ---------------------------------------------------------------

async function fetchDashboard(isRefresh = false) {
  if (isRefresh) {
    refreshing.value = true
  } else {
    loading.value = true
  }
  error.value = ''

  try {
    const res = await call('docbook.api.doctor.get_doctor_dashboard')

    if (!res) {
      throw new Error('No dashboard data returned.')
    }

    doctor.value = res.doctor || null
    stats.value = { ...stats.value, ...(res.stats || {}) }
    uniquePatients.value = res.unique_patients || 0
    todayAppointments.value = Array.isArray(res.today_appointments)
      ? res.today_appointments
      : []
    upcomingAppointments.value = Array.isArray(res.upcoming_appointments)
      ? res.upcoming_appointments
      : []
    recentPatients.value = Array.isArray(res.recent_patients)
      ? res.recent_patients
      : []
  } catch (err) {
    error.value = err?.message || 'Unable to load your dashboard. Please try again.'
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

// ---------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------

function formatTime(t) {
  if (!t) return '—'
  const [h, m] = String(t).split(':')
  const hour = parseInt(h, 10)
  if (Number.isNaN(hour)) return t
  const ampm = hour >= 12 ? 'PM' : 'AM'
  const displayHour = hour % 12 || 12
  return `${displayHour}:${(m || '00').slice(0, 2)} ${ampm}`
}

function formatFee(fee) {
  const n = Number(fee || 0)
  return n ? `₹${n.toLocaleString('en-IN')}` : 'Free'
}

function statusClass(status) {
  return `status-${(status || 'pending').toLowerCase()}`
}

function badgeTheme(status) {
  const s = (status || '').toLowerCase()
  if (s === 'confirmed') return 'green'
  if (s === 'completed') return 'blue'
  if (s === 'cancelled') return 'red'
  return 'amber'
}

function getInitials(name) {
  if (!name) return 'PT'
  return name.split(/\s+/).map((n) => n[0]).join('').slice(0, 2).toUpperCase()
}

function dayNum(d) {
  const dt = new Date(`${String(d).slice(0, 10)}T00:00:00`)
  return Number.isNaN(dt.getTime()) ? '–' : dt.getDate()
}

function monthShort(d) {
  const dt = new Date(`${String(d).slice(0, 10)}T00:00:00`)
  return Number.isNaN(dt.getTime()) ? '' : dt.toLocaleString('en-IN', { month: 'short' })
}

function isNowOrPast(appt) {
  const t = appt.appointment_time || '00:00:00'
  const dt = new Date(`${String(appt.appointment_date).slice(0, 10)}T${t}`)
  return !Number.isNaN(dt.getTime()) && dt <= new Date()
}

function openConsultation(appt) {
  if (appt?.name) router.push(`/consultation/${appt.name}`)
}

function go(path) {
  router.push(path)
}

onMounted(() => {
  fetchDashboard()
})
</script>

<template>
  <main class="dd-page">
    <div class="dd-shell">

      <!-- ============ Welcome header ============ -->
      <header class="dd-hero">
        <div class="dd-hero-glow" aria-hidden="true"></div>

        <div class="dd-hero-copy">
          <div class="dd-eyebrow">
            <span class="lucide-stethoscope"></span>
            DOCTOR PORTAL
          </div>

          <h1>{{ greeting }}, Dr. {{ firstName }}<span class="dot">.</span></h1>
          <p class="dd-hero-sub">{{ todayLabel }} — here's your practice at a glance.</p>

          <div class="dd-hero-badges" v-if="doctor">
            <span v-if="doctor.specialty" class="dd-chip">
              <span class="lucide-badge-check"></span>
              {{ doctor.specialty }}
            </span>
            <span v-if="doctor.qualification" class="dd-chip dd-chip--muted">
              {{ doctor.qualification }}
            </span>
            <span v-if="doctor.experience_years" class="dd-chip dd-chip--muted">
              {{ doctor.experience_years }} yrs exp
            </span>
            <span v-if="doctor.is_approved" class="dd-chip dd-chip--success">
              <span class="lucide-shield-check"></span>
              Approved
            </span>
          </div>
        </div>

        <div class="dd-hero-side">
          <div class="dd-avatar">
            <img v-if="doctor && doctor.profile_image" :src="doctor.profile_image" :alt="doctorName" />
            <span v-else class="dd-avatar-fallback">{{ doctorInitials }}</span>
          </div>
          <div class="dd-hero-actions">
            <Button
              label="Appointments"
              icon-left="lucide-calendar-check"
              @click="go('/doctor-appointments')"
            />
            <Button
              :loading="refreshing"
              :disabled="loading || refreshing"
              icon-left="lucide-refresh-cw"
              @click="fetchDashboard(true)"
            >
              Refresh
            </Button>
          </div>
        </div>
      </header>

      <!-- ============ Error ============ -->
      <section v-if="error" class="dd-error">
        <span class="lucide-circle-alert"></span>
        <div class="dd-error-copy">
          <strong>Unable to load your dashboard</strong>
          <p>{{ error }}</p>
        </div>
        <Button label="Try again" @click="fetchDashboard()" />
      </section>

      <template v-else>
        <!-- ============ Stat cards ============ -->
        <section class="dd-stats">
          <article class="dd-stat dd-stat--blue">
            <div class="dd-stat-icon"><span class="lucide-calendar-days"></span></div>
            <p class="dd-stat-label">Today's Appointments</p>
            <h2 class="dd-stat-value">{{ loading ? '—' : stats.today }}</h2>
            <span class="dd-stat-caption">Scheduled for today</span>
          </article>

          <article class="dd-stat dd-stat--teal">
            <div class="dd-stat-icon"><span class="lucide-clock-3"></span></div>
            <p class="dd-stat-label">Upcoming</p>
            <h2 class="dd-stat-value">{{ loading ? '—' : stats.upcoming }}</h2>
            <span class="dd-stat-caption">Confirmed &amp; pending ahead</span>
          </article>

          <article class="dd-stat dd-stat--amber">
            <div class="dd-stat-icon"><span class="lucide-hourglass"></span></div>
            <p class="dd-stat-label">Pending</p>
            <h2 class="dd-stat-value">{{ loading ? '—' : stats.pending }}</h2>
            <span class="dd-stat-caption">Awaiting confirmation</span>
          </article>

          <article class="dd-stat dd-stat--green">
            <div class="dd-stat-icon"><span class="lucide-users"></span></div>
            <p class="dd-stat-label">Patients</p>
            <h2 class="dd-stat-value">{{ loading ? '—' : uniquePatients }}</h2>
            <span class="dd-stat-caption">Unique patients seen</span>
          </article>

          <article class="dd-stat dd-stat--purple">
            <div class="dd-stat-icon"><span class="lucide-wallet"></span></div>
            <p class="dd-stat-label">Earnings</p>
            <h2 class="dd-stat-value">{{ loading ? '—' : formattedEarnings }}</h2>
            <span class="dd-stat-caption">From completed visits</span>
          </article>
        </section>

        <!-- ============ Main grid ============ -->
        <div class="dd-grid">

          <!-- Today's schedule -->
          <section class="dd-panel dd-panel--wide">
            <div class="dd-panel-head">
              <div>
                <div class="dd-eyebrow dd-eyebrow--dark">TODAY</div>
                <h2 class="dd-panel-title">Today's Schedule</h2>
              </div>
              <button class="dd-text-link" type="button" @click="go('/doctor-appointments')">
                View all <span class="lucide-arrow-up-right"></span>
              </button>
            </div>

            <div v-if="loading" class="dd-list">
              <div v-for="i in 3" :key="i" class="dd-skeleton"></div>
            </div>

            <div v-else-if="!todayAppointments.length" class="dd-empty">
              <div class="dd-empty-icon"><span class="lucide-calendar-off"></span></div>
              <h3>No appointments today</h3>
              <p>Enjoy the breather — your next visits are listed below.</p>
            </div>

            <div v-else class="dd-list">
              <article
                v-for="appt in todayAppointments"
                :key="appt.name"
                class="dd-appt"
                :class="{ 'dd-appt--past': isNowOrPast(appt) }"
              >
                <div class="dd-appt-time">
                  <span class="dd-appt-hour">{{ formatTime(appt.appointment_time) }}</span>
                  <span class="dd-appt-fee">{{ formatFee(appt.consultation_fee) }}</span>
                </div>

                <div class="dd-appt-avatar">{{ getInitials(appt.patient_name) }}</div>

                <div class="dd-appt-body">
                  <h3>{{ appt.patient_name || 'Patient' }}</h3>
                  <p class="dd-appt-meta">
                    <span v-if="appt.age">{{ appt.age }} yrs</span>
                    <span v-if="appt.gender">• {{ appt.gender }}</span>
                    <span v-if="appt.patient_phone">• {{ appt.patient_phone }}</span>
                  </p>
                  <p v-if="appt.reason" class="dd-appt-reason">
                    <span class="lucide-message-square"></span> {{ appt.reason }}
                  </p>
                </div>

                <div class="dd-appt-side">
                  <Badge :theme="badgeTheme(appt.status)">
                    {{ appt.status || 'Pending' }}
                  </Badge>
                  <button
                    class="dd-btn dd-btn--primary dd-btn--sm"
                    type="button"
                    @click="openConsultation(appt)"
                  >
                    Consult
                  </button>
                </div>
              </article>
            </div>
          </section>


          <!-- Upcoming + recent patients column -->
          <div class="dd-col">

            <!-- Upcoming -->
            <section class="dd-panel">
              <div class="dd-panel-head">
                <div>
                  <div class="dd-eyebrow dd-eyebrow--dark">NEXT UP</div>
                  <h2 class="dd-panel-title">Upcoming</h2>
                </div>
              </div>

              <div v-if="loading" class="dd-list">
                <div v-for="i in 3" :key="i" class="dd-skeleton dd-skeleton--sm"></div>
              </div>

              <div v-else-if="!upcomingAppointments.length" class="dd-empty dd-empty--sm">
                <div class="dd-empty-icon"><span class="lucide-calendar-check"></span></div>
                <h3>All clear</h3>
                <p>No upcoming appointments queued.</p>
              </div>

              <div v-else class="dd-list">
                <article v-for="appt in upcomingAppointments" :key="appt.name" class="dd-mini">
                  <div class="dd-mini-date">
                    <span class="dd-mini-day">{{ dayNum(appt.appointment_date) }}</span>
                    <span class="dd-mini-mon">{{ monthShort(appt.appointment_date) }}</span>
                  </div>
                  <div class="dd-mini-body">
                    <h3>{{ appt.patient_name || 'Patient' }}</h3>
                    <p>{{ formatTime(appt.appointment_time) }}</p>
                  </div>
                  <span class="dd-mini-status" :class="statusClass(appt.status)">
                    {{ appt.status || 'Pending' }}
                  </span>
                </article>
              </div>
            </section>

            <!-- Recent patients -->
            <section class="dd-panel">
              <div class="dd-panel-head">
                <div>
                  <div class="dd-eyebrow dd-eyebrow--dark">DIRECTORY</div>
                  <h2 class="dd-panel-title">Recent Patients</h2>
                </div>
                <button class="dd-text-link" type="button" @click="go('/doctor-patients')">
                  All <span class="lucide-arrow-up-right"></span>
                </button>
              </div>

              <div v-if="loading" class="dd-list">
                <div v-for="i in 3" :key="i" class="dd-skeleton dd-skeleton--sm"></div>
              </div>

              <div v-else-if="!recentPatients.length" class="dd-empty dd-empty--sm">
                <div class="dd-empty-icon"><span class="lucide-users"></span></div>
                <h3>No patients yet</h3>
                <p>Patients you treat will appear here.</p>
              </div>

              <div v-else class="dd-list">
                <article v-for="p in recentPatients" :key="p.name" class="dd-mini">
                  <div class="dd-mini-avatar">{{ getInitials(p.full_name) }}</div>
                  <div class="dd-mini-body">
                    <h3>{{ p.full_name || 'Patient' }}</h3>
                    <p>
                      <span v-if="p.age">{{ p.age }} yrs</span>
                      <span v-if="p.gender"> • {{ p.gender }}</span>
                      <span v-if="p.phone"> • {{ p.phone }}</span>
                    </p>
                  </div>
                </article>
              </div>
            </section>
          </div>
        </div>

        <!-- ============ Quick actions ============ -->
        <section class="dd-quick">
          <button class="dd-quick-btn" type="button" @click="go('/doctor-appointments')">
            <span class="dd-quick-icon dd-quick-icon--blue"><span class="lucide-calendar-check"></span></span>
            <span>My Appointments</span>
          </button>
          <button class="dd-quick-btn" type="button" @click="go('/doctor-patients')">
            <span class="dd-quick-icon dd-quick-icon--teal"><span class="lucide-users"></span></span>
            <span>My Patients</span>
          </button>
          <button class="dd-quick-btn" type="button" @click="go('/medicines')">
            <span class="dd-quick-icon dd-quick-icon--amber"><span class="lucide-book-open"></span></span>
            <span>Medicine Catalog</span>
          </button>
          <button class="dd-quick-btn" type="button" @click="go('/home')">
            <span class="dd-quick-icon dd-quick-icon--purple"><span class="lucide-search"></span></span>
            <span>Find Doctors</span>
          </button>
        </section>
      </template>
    </div>
  </main>
</template>


<style scoped>
.dd-page {
  min-height: 100%;
  padding: 32px 28px 64px;
  background:
    radial-gradient(circle at 12% 6%, rgba(13, 148, 136, 0.10), transparent 34%),
    radial-gradient(circle at 88% 10%, rgba(37, 99, 235, 0.08), transparent 30%),
    #f4f7fb;
  color: #0f172a;
}

.dd-shell { max-width: 1200px; margin: 0 auto; }

/* ---------- Hero ---------- */
.dd-hero {
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
  padding: 28px 30px;
  margin-bottom: 28px;
  border-radius: 24px;
  background: linear-gradient(120deg, #0f766e 0%, #0d9488 45%, #0e7490 100%);
  color: #fff;
  overflow: hidden;
  box-shadow: 0 16px 40px rgba(13, 118, 110, 0.28);
}

.dd-hero-glow {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 85% 20%, rgba(255, 255, 255, 0.18), transparent 40%),
    radial-gradient(circle at 60% 120%, rgba(255, 255, 255, 0.10), transparent 45%);
  pointer-events: none;
}

.dd-hero-copy { position: relative; z-index: 1; min-width: 0; flex: 1 1 320px; }

.dd-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1.2px;
  text-transform: uppercase;
  color: #99f6e4;
  margin-bottom: 10px;
}

.dd-eyebrow .lucide-stethoscope { font-size: 14px; }

.dd-eyebrow--dark { color: #0d9488; }

.dd-hero h1 {
  margin: 0 0 8px;
  font-size: 30px;
  font-weight: 800;
  letter-spacing: -0.5px;
  line-height: 1.15;
}

.dd-hero h1 .dot { color: #5eead4; }

.dd-hero-sub { margin: 0; font-size: 14px; color: rgba(255, 255, 255, 0.85); }

.dd-hero-badges { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }

.dd-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.16);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.22);
}

.dd-chip--muted { background: rgba(255, 255, 255, 0.10); color: rgba(255, 255, 255, 0.9); }

.dd-chip--success {
  background: rgba(16, 185, 129, 0.22);
  border-color: rgba(110, 231, 183, 0.4);
  color: #d1fae5;
}

.dd-hero-side {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 16px;
}

.dd-avatar {
  width: 84px;
  height: 84px;
  border-radius: 22px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.18);
  border: 2px solid rgba(255, 255, 255, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
}

.dd-avatar img { width: 100%; height: 100%; object-fit: cover; }

.dd-avatar-fallback { font-size: 26px; font-weight: 800; color: #fff; letter-spacing: 1px; }

.dd-hero-actions { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }

/* ---------- Error ---------- */
.dd-error {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 20px;
  margin-bottom: 24px;
  border-radius: 16px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
}

.dd-error .lucide-circle-alert { font-size: 22px; flex-shrink: 0; }
.dd-error-copy { flex: 1; min-width: 0; }
.dd-error-copy strong { display: block; font-size: 14px; }
.dd-error-copy p { margin: 2px 0 0; font-size: 13px; }

/* ---------- Stats ---------- */
.dd-stats {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  margin-bottom: 28px;
}

.dd-stat {
  position: relative;
  padding: 20px;
  border-radius: 20px;
  background: #fff;
  border: 1px solid #eef2f7;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
  overflow: hidden;
}

.dd-stat::after {
  content: '';
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  background: var(--accent, #0d9488);
}

.dd-stat--blue { --accent: #2563eb; }
.dd-stat--teal { --accent: #0d9488; }
.dd-stat--amber { --accent: #f59e0b; }
.dd-stat--green { --accent: #10b981; }
.dd-stat--purple { --accent: #8b5cf6; }

.dd-stat-icon {
  width: 42px;
  height: 42px;
  border-radius: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  margin-bottom: 14px;
  background: color-mix(in srgb, var(--accent) 12%, white);
  color: var(--accent);
}

.dd-stat-label {
  margin: 0;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.dd-stat-value {
  margin: 4px 0 2px;
  font-size: 30px;
  font-weight: 800;
  letter-spacing: -1px;
  color: #0f172a;
  line-height: 1.1;
}

.dd-stat-caption { font-size: 12px; color: #94a3b8; }


/* ---------- Grid ---------- */
.dd-grid {
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 20px;
  align-items: start;
}

.dd-col { display: flex; flex-direction: column; gap: 20px; }

.dd-panel {
  background: #fff;
  border: 1px solid #eef2f7;
  border-radius: 20px;
  padding: 22px;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
}

.dd-panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.dd-panel-title { margin: 2px 0 0; font-size: 18px; font-weight: 800; letter-spacing: -0.3px; }

.dd-text-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
  color: #0d9488;
}
.dd-text-link:hover { text-decoration: underline; }

/* ---------- Appointment list ---------- */
.dd-list { display: flex; flex-direction: column; gap: 10px; }

.dd-appt {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid #eef2f7;
  background: #f8fafc;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.dd-appt:hover { border-color: #cbd5e1; box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06); }
.dd-appt--past { opacity: 0.72; }

.dd-appt-time {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 74px;
  padding-right: 14px;
  border-right: 1px solid #e2e8f0;
}

.dd-appt-hour { font-size: 15px; font-weight: 800; color: #0f172a; }
.dd-appt-fee { font-size: 11px; color: #0d9488; font-weight: 700; margin-top: 2px; }

.dd-appt-avatar {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0d9488;
  color: #fff;
  font-size: 13px;
  font-weight: 800;
}

.dd-appt-body { flex: 1; min-width: 0; }
.dd-appt-body h3 { margin: 0; font-size: 14px; font-weight: 700; }
.dd-appt-meta { margin: 2px 0 0; font-size: 12px; color: #64748b; }

.dd-appt-reason {
  margin: 6px 0 0;
  font-size: 12px;
  color: #475569;
  display: flex;
  align-items: center;
  gap: 5px;
}

.dd-appt-side { display: flex; flex-direction: column; align-items: flex-end; gap: 8px; }


/* ---------- Mini rows ---------- */
.dd-mini {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 13px;
  border-radius: 13px;
  border: 1px solid #eef2f7;
  background: #f8fafc;
}

.dd-mini-date {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 11px;
  background: #eff6ff;
  color: #1d4ed8;
  flex-shrink: 0;
}

.dd-mini-day { font-size: 16px; font-weight: 800; line-height: 1; }
.dd-mini-mon { font-size: 10px; font-weight: 700; text-transform: uppercase; }

.dd-mini-avatar {
  width: 38px;
  height: 38px;
  border-radius: 11px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e0f2fe;
  color: #0369a1;
  font-size: 13px;
  font-weight: 800;
}

.dd-mini-body { flex: 1; min-width: 0; }
.dd-mini-body h3 {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dd-mini-body p { margin: 1px 0 0; font-size: 11px; color: #64748b; }

.dd-mini-status {
  flex-shrink: 0;
  font-size: 10px;
  font-weight: 700;
  padding: 3px 9px;
  border-radius: 999px;
  text-transform: capitalize;
}
.dd-mini-status.status-pending { background: #fffbeb; color: #b45309; }
.dd-mini-status.status-confirmed { background: #ecfdf5; color: #047857; }
.dd-mini-status.status-completed { background: #eff6ff; color: #1d4ed8; }
.dd-mini-status.status-cancelled { background: #fef2f2; color: #b91c1c; }

/* ---------- Buttons ---------- */
.dd-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 700;
  border: 1px solid transparent;
  cursor: pointer;
  transition: background 0.15s, box-shadow 0.15s, transform 0.1s;
}
.dd-btn:active { transform: scale(0.97); }
.dd-btn--primary { background: #0d9488; color: #fff; }
.dd-btn--primary:hover { background: #0f766e; }
.dd-btn--sm { padding: 6px 12px; font-size: 11px; }

/* ---------- Empty ---------- */
.dd-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 40px 20px;
  border: 1px dashed #cbd5e1;
  border-radius: 16px;
  color: #475569;
}
.dd-empty--sm { padding: 26px 16px; }

.dd-empty-icon {
  width: 52px;
  height: 52px;
  border-radius: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  background: #f0fdfa;
  color: #0d9488;
  margin-bottom: 14px;
}
.dd-empty h3 { margin: 0 0 4px; font-size: 15px; color: #0f172a; }
.dd-empty p { margin: 0; font-size: 13px; }

/* ---------- Skeletons ---------- */
.dd-skeleton {
  height: 68px;
  border-radius: 14px;
  background: #eef2f7;
  animation: dd-pulse 1.5s infinite;
}
.dd-skeleton--sm { height: 52px; }

@keyframes dd-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.55; }
}


/* ---------- Quick actions ---------- */
.dd-quick {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-top: 24px;
}

.dd-quick-btn {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 18px;
  border-radius: 16px;
  border: 1px solid #eef2f7;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04);
  transition: transform 0.12s, box-shadow 0.15s, border-color 0.15s;
  text-align: left;
}

.dd-quick-btn:hover {
  transform: translateY(-2px);
  border-color: #cbd5e1;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}

.dd-quick-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}
.dd-quick-icon--blue { background: #eff6ff; color: #2563eb; }
.dd-quick-icon--teal { background: #f0fdfa; color: #0d9488; }
.dd-quick-icon--amber { background: #fffbeb; color: #d97706; }
.dd-quick-icon--purple { background: #f5f3ff; color: #7c3aed; }

/* ---------- Responsive ---------- */
@media (max-width: 1024px) {
  .dd-stats { grid-template-columns: repeat(3, 1fr); }
  .dd-grid { grid-template-columns: 1fr; }
  .dd-quick { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 640px) {
  .dd-page { padding: 20px 14px 48px; }
  .dd-hero { padding: 22px 20px; }
  .dd-hero h1 { font-size: 24px; }
  .dd-hero-side { align-items: flex-start; width: 100%; }
  .dd-hero-actions { justify-content: flex-start; }
  .dd-stats { grid-template-columns: repeat(2, 1fr); gap: 12px; }
  .dd-stat { padding: 16px; }
  .dd-stat-value { font-size: 24px; }
  .dd-panel { padding: 16px; }
  .dd-appt { flex-wrap: wrap; }
  .dd-appt-side { flex-direction: row; align-items: center; width: 100%; justify-content: space-between; }
  .dd-quick { grid-template-columns: 1fr; }
}

@media (max-width: 400px) {
  .dd-stats { grid-template-columns: 1fr; }
}
</style>

