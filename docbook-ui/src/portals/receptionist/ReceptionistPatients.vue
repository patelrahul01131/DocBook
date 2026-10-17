<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { call } from '../../api'

const route = useRoute()
const router = useRouter()

const searchQuery = ref('')
const searchPhone = ref('')
const patients = ref([])
const loading = ref(false)
const error = ref(null)

// Detailed patient view
const selectedPatient = ref(null)
const recordDetails = ref(null)
const recordLoading = ref(false)
const recordError = ref(null)
const activeTab = ref('appointments')

// Appointment detail modal
const showApptModal = ref(false)
const selectedAppt = ref(null)
const loadingApptDetail = ref(false)
const apptDetailError = ref(null)

async function openAppointmentDetail(appt) {
  if (!appt) return
  selectedAppt.value = { ...appt }
  showApptModal.value = true
  loadingApptDetail.value = true
  apptDetailError.value = null

  try {
    const res = await call('docbook.api.appointment.show_appointment', {
      appointment_id: appt.name,
    })
    if (res) {
      selectedAppt.value = { ...appt, ...res }
    }
  } catch (err) {
    apptDetailError.value = err.message || 'Failed to fetch detailed appointment record.'
  } finally {
    loadingApptDetail.value = false
  }
}

function closeApptModal() {
  showApptModal.value = false
  selectedAppt.value = null
  apptDetailError.value = null
}

async function searchPatients() {
  loading.value = true
  error.value = null
  try {
    const res = await call('docbook.api.queue.search_patient_directory', {
      query: searchQuery.value || undefined,
      phone: searchPhone.value || undefined,
      limit: 50,
    })
    patients.value = Array.isArray(res?.results) ? res.results : []
    // If exact 1 result or query matches one, auto-select
    if (patients.value.length === 1 && !selectedPatient.value) {
      selectPatient(patients.value[0])
    }
  } catch (err) {
    error.value = err.message || 'Failed to search patients.'
  } finally {
    loading.value = false
  }
}

async function selectPatient(patient) {
  selectedPatient.value = patient
  recordLoading.value = true
  recordError.value = null
  recordDetails.value = null
  activeTab.value = 'appointments'

  try {
    const res = await call('docbook.api.queue.get_patient_records', {
      patient: patient.name,
    })
    recordDetails.value = res
  } catch (err) {
    recordError.value = err.message || 'Failed to load patient records.'
  } finally {
    recordLoading.value = false
  }
}

function formatDate(d) {
  if (!d) return '—'
  try {
    return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  } catch {
    return d
  }
}

function formatTime(t) {
  if (!t) return ''
  const parts = String(t).split(':')
  if (parts.length >= 2) {
    let h = parseInt(parts[0], 10)
    const m = parts[1]
    const ampm = h >= 12 ? 'PM' : 'AM'
    h = h % 12 || 12
    return `${h}:${m} ${ampm}`
  }
  return t
}

onMounted(() => {
  if (route.query.search) {
    searchQuery.value = String(route.query.search)
  }
  searchPatients()
})

watch(() => route.query.search, (val) => {
  if (val) {
    searchQuery.value = String(val)
    searchPatients()
  }
})
</script>

<template>
  <main class="rec-patients-page">
    <div class="rec-shell">

      <!-- Header -->
      <header class="page-head">
        <div>
          <div class="eyebrow">PATIENT DIRECTORY & COMPREHENSIVE RECORDS</div>
          <h1>Patients & Medical History<span>.</span></h1>
          <p class="head-sub">
            Search any registered patient to view their complete history, upcoming & past appointments, active prescriptions, and lab reports.
          </p>
        </div>
      </header>

      <!-- Main Split Layout -->
      <div class="layout-grid">

        <!-- Left Pane: Search & Directory List -->
        <section class="left-pane">
          <div class="search-box-card">
            <div class="input-row">
              <input
                v-model="searchQuery"
                type="text"
                class="search-text-input"
                placeholder="Search by patient name, email..."
                @keyup.enter="searchPatients"
              />
              <input
                v-model="searchPhone"
                type="text"
                class="search-phone-input"
                placeholder="Phone..."
                @keyup.enter="searchPatients"
              />
              <button class="btn-search" :disabled="loading" @click="searchPatients">
                {{ loading ? '…' : 'Search' }}
              </button>
            </div>
          </div>

          <!-- Directory List -->
          <div class="patient-list-card">
            <div class="list-head">
              <span class="count-badge">{{ patients.length }} Patients Found</span>
            </div>

            <div v-if="loading && !patients.length" class="loading-state">
              Searching directory…
            </div>

            <div v-else-if="!patients.length" class="empty-list">
              No patients found. Try another search term.
            </div>

            <div v-else class="patients-scroll-list">
              <article
                v-for="p in patients"
                :key="p.name"
                class="patient-list-item"
                :class="{ active: selectedPatient?.name === p.name }"
                @click="selectPatient(p)"
              >
                <div class="item-avatar">{{ (p.full_name || p.name || 'P').charAt(0).toUpperCase() }}</div>
                <div class="item-body">
                  <div class="item-name">{{ p.full_name || p.name }}</div>
                  <div class="item-meta">
                    <span v-if="p.age">{{ p.age }} yrs</span>
                    <span v-if="p.gender"> · {{ p.gender }}</span>
                    <span v-if="p.phone"> · 📞 {{ p.phone }}</span>
                  </div>
                  <div class="item-stats-chips">
                    <span class="chip chip-visits">{{ p.total_appointments || 0 }} visits</span>
                    <span v-if="p.upcoming_appointments" class="chip chip-up">{{ p.upcoming_appointments }} upcoming</span>
                  </div>
                </div>
                <span class="arrow-indicator">→</span>
              </article>
            </div>
          </div>
        </section>

        <!-- Right Pane: Comprehensive Patient Record Details -->
        <section class="right-pane">
          <!-- When no patient selected -->
          <div v-if="!selectedPatient" class="placeholder-card">
            <div class="placeholder-icon">👤</div>
            <h3>Select a Patient</h3>
            <p>Click on any patient from the left directory list to view their complete appointments, prescriptions, and clinical history.</p>
          </div>

          <!-- Loading state -->
          <div v-else-if="recordLoading" class="placeholder-card">
            <div class="loader-spinner"></div>
            <p>Loading patient records for {{ selectedPatient.full_name || selectedPatient.name }}…</p>
          </div>

          <!-- Error state -->
          <div v-else-if="recordError" class="error-panel">
            <p>{{ recordError }}</p>
            <button class="btn-secondary" @click="selectPatient(selectedPatient)">Retry</button>
          </div>

          <!-- Full Record Container -->
          <div v-else-if="recordDetails" class="record-container">

            <!-- Profile Summary Banner -->
            <div class="patient-profile-banner">
              <div class="banner-avatar">
                {{ (recordDetails.patient?.full_name || recordDetails.patient?.name || 'P').charAt(0).toUpperCase() }}
              </div>
              <div class="banner-info">
                <h2>{{ recordDetails.patient?.full_name || recordDetails.patient?.name }}</h2>
                <div class="banner-sub">
                  <span v-if="recordDetails.patient?.age">{{ recordDetails.patient.age }} years old</span>
                  <span v-if="recordDetails.patient?.gender"> · {{ recordDetails.patient.gender }}</span>
                  <span v-if="recordDetails.patient?.phone"> · 📞 {{ recordDetails.patient.phone }}</span>
                  <span v-if="recordDetails.patient?.user"> · ✉️ {{ recordDetails.patient.user }}</span>
                </div>
              </div>

              <!-- Quick Lifetime Stats -->
              <div class="profile-stats-grid">
                <div class="pstat">
                  <span>Total Visits</span>
                  <strong>{{ recordDetails.stats?.total_appointments || 0 }}</strong>
                </div>
                <div class="pstat">
                  <span>Upcoming</span>
                  <strong style="color: #2563eb;">{{ recordDetails.stats?.upcoming || 0 }}</strong>
                </div>
                <div class="pstat">
                  <span>Running Rx</span>
                  <strong style="color: #059669;">{{ recordDetails.stats?.active_prescriptions || 0 }}</strong>
                </div>
                <div class="pstat">
                  <span>Reports</span>
                  <strong>{{ recordDetails.stats?.reports || 0 }}</strong>
                </div>
              </div>
            </div>

            <!-- Tab Navigation -->
            <div class="record-tabs">
              <button
                class="tab-btn"
                :class="{ active: activeTab === 'appointments' }"
                @click="activeTab = 'appointments'"
              >
                📅 Appointments ({{ (recordDetails.upcoming?.length || 0) + (recordDetails.past?.length || 0) }})
              </button>
              <button
                class="tab-btn"
                :class="{ active: activeTab === 'prescriptions' }"
                @click="activeTab = 'prescriptions'"
              >
                💊 Prescriptions & Medicines ({{ recordDetails.prescriptions?.length || 0 }})
              </button>
              <button
                class="tab-btn"
                :class="{ active: activeTab === 'history' }"
                @click="activeTab = 'history'"
              >
                📋 Medical History ({{ recordDetails.medical_history?.length || 0 }})
              </button>
              <button
                class="tab-btn"
                :class="{ active: activeTab === 'reports' }"
                @click="activeTab = 'reports'"
              >
                🧪 Lab & Imaging Reports ({{ recordDetails.reports?.length || 0 }})
              </button>
            </div>

            <!-- TAB 1: APPOINTMENTS (PAST & FUTURE) -->
            <div v-if="activeTab === 'appointments'" class="tab-content">
              <!-- Upcoming Section -->
              <div class="sub-section">
                <h3 class="section-title">
                  <span class="title-dot blue"></span> Upcoming Appointments ({{ recordDetails.upcoming?.length || 0 }})
                </h3>
                <div v-if="!recordDetails.upcoming?.length" class="empty-sub">
                  No upcoming appointments booked.
                </div>
                <div v-else class="appt-grid">
                  <article
                    v-for="a in recordDetails.upcoming"
                    :key="a.name"
                    class="appt-card appt-card--upcoming clickable"
                    @click="openAppointmentDetail(a)"
                  >
                    <div class="appt-top">
                      <div>
                        <div class="appt-date">📅 {{ formatDate(a.appointment_date) }} at {{ formatTime(a.appointment_time) }}</div>
                        <div class="appt-doctor">Dr. {{ a.doctor_name || a.doctor }}</div>
                      </div>
                      <span class="status-pill status-upcoming">{{ a.visit_stage || a.status }}</span>
                    </div>
                    <div v-if="a.reason" class="appt-reason"><strong>Reason:</strong> {{ a.reason }}</div>
                    <div v-if="a.symptoms" class="appt-symptoms"><strong>Symptoms:</strong> {{ a.symptoms }}</div>
                    <div class="appt-footer">
                      <span v-if="a.queue_token" class="token-badge">Token #{{ a.queue_token }}</span>
                      <span v-if="a.checked_in" class="checked-in-text">✅ Checked in</span>
                      <span v-else class="not-checked-text">Pending arrival</span>
                      <span class="appt-click-hint">View Details →</span>
                    </div>
                  </article>
                </div>
              </div>

              <!-- Past Appointments Section -->
              <div class="sub-section">
                <h3 class="section-title">
                  <span class="title-dot gray"></span> Past Consultations & Visits ({{ recordDetails.past?.length || 0 }})
                </h3>
                <div v-if="!recordDetails.past?.length" class="empty-sub">
                  No past consultation history on file.
                </div>
                <div v-else class="appt-grid">
                  <article
                    v-for="a in recordDetails.past"
                    :key="a.name"
                    class="appt-card appt-card--past clickable"
                    @click="openAppointmentDetail(a)"
                  >
                    <div class="appt-top">
                      <div>
                        <div class="appt-date">📅 {{ formatDate(a.appointment_date) }} at {{ formatTime(a.appointment_time) }}</div>
                        <div class="appt-doctor">Dr. {{ a.doctor_name || a.doctor }}</div>
                      </div>
                      <span class="status-pill status-past">{{ a.status }}</span>
                    </div>
                    <div v-if="a.diagnosis" class="diagnosis-highlight">
                      <strong>Diagnosis:</strong> {{ a.diagnosis }}
                    </div>
                    <div v-if="a.reason" class="appt-reason"><strong>Chief Complaint:</strong> {{ a.reason }}</div>
                    <div v-if="a.symptoms" class="appt-symptoms"><strong>Symptoms:</strong> {{ a.symptoms }}</div>
                    <div class="appt-footer">
                      <span class="appt-click-hint">View Consultation Dossier & Prescriptions →</span>
                    </div>
                  </article>
                </div>
              </div>
            </div>

            <!-- TAB 2: RUNNING PRESCRIPTIONS & MEDICINES -->
            <div v-if="activeTab === 'prescriptions'" class="tab-content">
              <div v-if="!recordDetails.prescriptions?.length" class="empty-sub">
                No prescription records found for this patient.
              </div>
              <div v-else class="prescriptions-stack">
                <article
                  v-for="p in recordDetails.prescriptions"
                  :key="p.name"
                  class="prescription-box"
                  :class="{ 'is-running': p.running }"
                >
                  <div class="prx-header">
                    <div>
                      <div class="prx-title">
                        Prescription #{{ p.name }}
                        <span v-if="p.running" class="running-pill">● RUNNING / ACTIVE</span>
                        <span v-else class="completed-pill">Completed</span>
                      </div>
                      <div class="prx-meta">
                        Prescribed by Dr. {{ p.doctor_name || p.doctor }} on {{ formatDate(p.prescription_date) }}
                      </div>
                    </div>
                    <div v-if="p.diagnosis" class="prx-dx">
                      <strong>Diagnosis:</strong> {{ p.diagnosis }}
                    </div>
                  </div>

                  <!-- Medicines Table -->
                  <div class="prx-meds-table-wrap">
                    <table class="meds-table">
                      <thead>
                        <tr>
                          <th>Medicine</th>
                          <th>Dosage</th>
                          <th>Frequency</th>
                          <th>Duration / Dates</th>
                          <th>Instructions</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="m in p.medicines" :key="m.name">
                          <td class="font-bold text-slate-900">{{ m.prescribed_medicine_name || m.medicine }}</td>
                          <td>{{ m.dosage || 'Standard' }}</td>
                          <td><span class="freq-tag">{{ m.frequency || 'Once Daily' }}</span></td>
                          <td>
                            <span v-if="m.start_date">{{ formatDate(m.start_date) }} → {{ formatDate(m.end_date) }}</span>
                            <span v-else>Ongoing</span>
                          </td>
                          <td class="text-xs text-slate-600">{{ m.instructions || 'As advised' }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  <div v-if="p.instructions || p.notes" class="prx-instructions">
                    <div v-if="p.instructions"><strong>Instructions:</strong> {{ p.instructions }}</div>
                    <div v-if="p.notes"><strong>Doctor's Notes:</strong> {{ p.notes }}</div>
                  </div>
                </article>
              </div>
            </div>

            <!-- TAB 3: MEDICAL HISTORY -->
            <div v-if="activeTab === 'history'" class="tab-content">
              <div v-if="!recordDetails.medical_history?.length" class="empty-sub">
                No past medical history conditions recorded.
              </div>
              <div v-else class="history-grid">
                <div
                  v-for="h in recordDetails.medical_history"
                  :key="h.name"
                  class="history-card"
                >
                  <div class="h-top">
                    <h4>{{ h.medical_condition }}</h4>
                    <span class="severity-pill" :class="`sev-${(h.severity || 'mild').toLowerCase()}`">
                      {{ h.severity || 'Mild' }}
                    </span>
                  </div>
                  <div class="h-date text-xs text-slate-400">Recorded: {{ formatDate(h.record_date) }} · Status: {{ h.status }}</div>
                  <div v-if="h.description" class="h-desc">{{ h.description }}</div>
                  <div v-if="h.symptoms" class="h-symptoms"><strong>Symptoms:</strong> {{ h.symptoms }}</div>
                  <div v-if="h.allergies" class="h-allergies">⚠️ <strong>Allergies:</strong> {{ h.allergies }}</div>
                  <div v-if="h.current_medications" class="h-meds">💊 <strong>Current Meds:</strong> {{ h.current_medications }}</div>
                </div>
              </div>
            </div>

            <!-- TAB 4: LAB & IMAGING REPORTS -->
            <div v-if="activeTab === 'reports'" class="tab-content">
              <div v-if="!recordDetails.reports?.length" class="empty-sub">
                No medical reports on file for this patient.
              </div>
              <div v-else class="reports-grid">
                <div v-for="r in recordDetails.reports" :key="r.name" class="report-card">
                  <div class="r-top">
                    <div>
                      <h4>{{ r.title }}</h4>
                      <span class="r-type">{{ r.report_type }} · {{ r.laboratory || 'Hospital Lab' }}</span>
                    </div>
                    <span class="r-status" :class="`r-status--${(r.status || 'pending').toLowerCase()}`">
                      {{ r.status }}
                    </span>
                  </div>
                  <div v-if="r.findings" class="r-findings">
                    <strong>Findings:</strong> {{ r.findings }}
                  </div>
                  <div class="r-date text-xs text-slate-400">Date: {{ formatDate(r.creation) }}</div>
                  <a
                    v-if="r.report_file"
                    :href="r.report_file"
                    target="_blank"
                    class="btn-file-link"
                  >
                    📄 View Report Document
                  </a>
                </div>
              </div>
            </div>

          </div>
        </section>

      </div>

      <!-- Appointment Detailed Modal -->
      <div v-if="showApptModal && selectedAppt" class="modal-backdrop" @click.self="closeApptModal">
        <div class="modal-card modal-card--lg" role="dialog" aria-modal="true">
          <!-- Modal Header -->
          <div class="modal-header">
            <div>
              <div class="modal-eyebrow-row">
                <span class="modal-eyebrow">CONSULTATION & APPOINTMENT DOSSIER</span>
                <span class="status-pill" :class="selectedAppt.status === 'Completed' ? 'status-past' : 'status-upcoming'">
                  {{ selectedAppt.visit_stage || selectedAppt.status }}
                </span>
                <span v-if="selectedAppt.queue_token" class="token-badge">Token #{{ selectedAppt.queue_token }}</span>
                <span v-if="selectedAppt.fast_track" class="fast-track-pill">⚡ Fast Track</span>
              </div>
              <h2 class="modal-headline">Appointment {{ selectedAppt.name }}</h2>
              <div class="modal-datetime">
                📅 {{ formatDate(selectedAppt.appointment_date) }} &nbsp;•&nbsp; ⏰ {{ formatTime(selectedAppt.appointment_time) }}
              </div>
            </div>
            <button class="modal-close-btn" @click="closeApptModal" aria-label="Close">✕</button>
          </div>

          <!-- Modal Body -->
          <div class="modal-body">
            <div v-if="loadingApptDetail" class="detail-loading-banner">
              <span class="loader-spinner-sm"></span> Loading complete clinical notes, prescriptions and reports...
            </div>

            <div v-if="apptDetailError" class="modal-error-banner">
              ⚠️ {{ apptDetailError }}
            </div>

            <!-- Doctor & Patient Overview Cards -->
            <div class="dossier-people-grid">
              <div class="dossier-card doctor-side">
                <div class="dc-icon">🩺</div>
                <div class="dc-info">
                  <div class="dc-label">Consulting Doctor</div>
                  <div class="dc-name">Dr. {{ selectedAppt.doctor_data?.full_name || selectedAppt.doctor_name || selectedAppt.doctor }}</div>
                  <div class="dc-sub">
                    <span v-if="selectedAppt.doctor_data?.specialty">{{ selectedAppt.doctor_data.specialty }}</span>
                    <span v-if="selectedAppt.doctor_data?.qualification"> • {{ selectedAppt.doctor_data.qualification }}</span>
                  </div>
                  <div v-if="selectedAppt.doctor_data?.phone" class="dc-contact">📞 {{ selectedAppt.doctor_data.phone }}</div>
                </div>
              </div>

              <div class="dossier-card patient-side">
                <div class="dc-icon">👤</div>
                <div class="dc-info">
                  <div class="dc-label">Patient Profile</div>
                  <div class="dc-name">{{ selectedAppt.patient_data?.full_name || selectedPatient?.full_name || selectedAppt.patient }}</div>
                  <div class="dc-sub">
                    <span v-if="selectedAppt.patient_data?.age || selectedPatient?.age">{{ selectedAppt.patient_data?.age || selectedPatient?.age }} yrs</span>
                    <span v-if="selectedAppt.patient_data?.gender || selectedPatient?.gender"> • {{ selectedAppt.patient_data?.gender || selectedPatient?.gender }}</span>
                    <span v-if="selectedAppt.patient_data?.phone || selectedPatient?.phone"> • 📞 {{ selectedAppt.patient_data?.phone || selectedPatient?.phone }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Clinical Assessment & Consultation Notes -->
            <div class="dossier-section">
              <h4 class="dossier-title">🩺 Clinical Assessment & Consultation Notes</h4>
              <div class="dossier-grid">
                <div class="dossier-item">
                  <span class="dossier-item-label">Chief Complaint / Reason</span>
                  <div class="dossier-item-value">{{ selectedAppt.reason || 'None specified' }}</div>
                </div>
                <div class="dossier-item">
                  <span class="dossier-item-label">Reported Symptoms</span>
                  <div class="dossier-item-value">{{ selectedAppt.symptoms || 'None recorded' }}</div>
                </div>
                <div class="dossier-item span-full diagnosis-item">
                  <span class="dossier-item-label">Clinical Diagnosis</span>
                  <div class="dossier-item-value diagnosis-val">{{ selectedAppt.diagnosis || 'Pending / No diagnosis recorded' }}</div>
                </div>
                <div v-if="selectedAppt.consultation_notes" class="dossier-item span-full">
                  <span class="dossier-item-label">Doctor's Consultation Notes</span>
                  <div class="dossier-item-value pre-wrap">{{ selectedAppt.consultation_notes }}</div>
                </div>
                <div v-if="selectedAppt.treatment_plan" class="dossier-item span-full">
                  <span class="dossier-item-label">Treatment Plan & Medical Advice</span>
                  <div class="dossier-item-value pre-wrap">{{ selectedAppt.treatment_plan }}</div>
                </div>
                <div v-if="selectedAppt.follow_up_date || selectedAppt.follow_up_instructions" class="dossier-item span-full followup-item">
                  <span class="dossier-item-label">Follow-Up Instructions</span>
                  <div class="dossier-item-value">
                    <strong v-if="selectedAppt.follow_up_date">Follow-up on: {{ formatDate(selectedAppt.follow_up_date) }}</strong>
                    <span v-if="selectedAppt.follow_up_instructions"> — {{ selectedAppt.follow_up_instructions }}</span>
                  </div>
                </div>
                <div v-if="selectedAppt.referral" class="dossier-item span-full">
                  <span class="dossier-item-label">Referral / Care Episode</span>
                  <div class="dossier-item-value font-mono">{{ selectedAppt.referral }}</div>
                </div>
              </div>
            </div>

            <!-- Prescriptions & Prescribed Medicines -->
            <div class="dossier-section">
              <h4 class="dossier-title">
                💊 Prescribed Medicines
                <span class="dossier-count" v-if="selectedAppt.prescriptions?.length">
                  ({{ selectedAppt.prescriptions.reduce((acc, p) => acc + (p.medicines?.length || 0), 0) }})
                </span>
              </h4>

              <div v-if="!selectedAppt.prescriptions || !selectedAppt.prescriptions.length" class="dossier-empty">
                No prescriptions issued for this consultation.
              </div>
              <div v-else class="modal-prx-list">
                <div v-for="prx in selectedAppt.prescriptions" :key="prx.name" class="modal-prx-item">
                  <div class="modal-prx-item-head">
                    <div>
                      <span class="font-bold text-slate-900">Prescription #{{ prx.name }}</span>
                      <span class="text-xs text-slate-500 ml-2">Date: {{ formatDate(prx.prescription_date) }}</span>
                    </div>
                    <span v-if="prx.status" class="status-pill status-past">{{ prx.status }}</span>
                  </div>

                  <div v-if="prx.medicines && prx.medicines.length" class="prx-meds-table-wrap">
                    <table class="meds-table">
                      <thead>
                        <tr>
                          <th>Medicine</th>
                          <th>Dosage</th>
                          <th>Frequency</th>
                          <th>Route</th>
                          <th>Duration</th>
                          <th>Instructions</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="m in prx.medicines" :key="m.name">
                          <td class="font-bold text-slate-900">{{ m.prescribed_medicine_name || m.medicine }}</td>
                          <td>{{ m.dosage || 'Standard' }}</td>
                          <td><span class="freq-tag">{{ m.frequency || 'Once Daily' }}</span></td>
                          <td>{{ m.route || 'Oral' }}</td>
                          <td>
                            <span v-if="m.start_date">{{ formatDate(m.start_date) }} → {{ formatDate(m.end_date) }}</span>
                            <span v-else>As directed</span>
                          </td>
                          <td class="text-xs text-slate-600">{{ m.instructions || '—' }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  <div v-if="prx.instructions || prx.notes" class="prx-instructions mt-2">
                    <div v-if="prx.instructions"><strong>Instructions:</strong> {{ prx.instructions }}</div>
                    <div v-if="prx.notes"><strong>Doctor's Notes:</strong> {{ prx.notes }}</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Lab & Imaging Diagnostic Reports -->
            <div class="dossier-section">
              <h4 class="dossier-title">
                🧪 Ordered Lab & Diagnostic Reports
                <span class="dossier-count" v-if="selectedAppt.reports?.length">({{ selectedAppt.reports.length }})</span>
              </h4>

              <div v-if="!selectedAppt.reports || !selectedAppt.reports.length" class="dossier-empty">
                No lab or imaging reports linked to this appointment.
              </div>
              <div v-else class="modal-reports-grid">
                <div v-for="r in selectedAppt.reports" :key="r.name" class="report-card">
                  <div class="r-top">
                    <div>
                      <h4 class="font-bold">{{ r.title }}</h4>
                      <span class="r-type">{{ r.report_type }} • {{ r.laboratory || 'Hospital Diagnostics' }}</span>
                    </div>
                    <span class="r-status" :class="`r-status--${(r.status || 'pending').toLowerCase()}`">
                      {{ r.status }}
                    </span>
                  </div>
                  <div v-if="r.findings" class="r-findings mt-2">
                    <strong>Findings:</strong> {{ r.findings }}
                  </div>
                  <div v-if="r.description" class="text-xs text-slate-600 mt-1">
                    {{ r.description }}
                  </div>
                  <a
                    v-if="r.report_file"
                    :href="r.report_file"
                    target="_blank"
                    class="btn-file-link mt-2 inline-block"
                  >
                    📄 View / Download Report Document
                  </a>
                </div>
              </div>
            </div>

            <!-- Queue & Hospital Check-in Status -->
            <div class="dossier-section">
              <h4 class="dossier-title">🏥 Hospital Queue & Check-in Details</h4>
              <div class="queue-meta-grid">
                <div class="qmeta-item">
                  <span class="qmeta-label">Check-in Status</span>
                  <span class="qmeta-val">{{ selectedAppt.checked_in ? '✅ Checked In' : '⏳ Pending Arrival' }}</span>
                </div>
                <div v-if="selectedAppt.checked_in_at" class="qmeta-item">
                  <span class="qmeta-label">Checked-in Time</span>
                  <span class="qmeta-val">{{ selectedAppt.checked_in_at }}</span>
                </div>
                <div v-if="selectedAppt.called_at" class="qmeta-item">
                  <span class="qmeta-label">Called into Room</span>
                  <span class="qmeta-val">{{ selectedAppt.called_at }}</span>
                </div>
                <div class="qmeta-item">
                  <span class="qmeta-label">Visit Stage</span>
                  <span class="qmeta-val capitalize">{{ selectedAppt.visit_stage || 'Scheduled' }}</span>
                </div>
                <div v-if="selectedAppt.consultation_fee" class="qmeta-item">
                  <span class="qmeta-label">Consultation Fee</span>
                  <span class="qmeta-val">₹{{ selectedAppt.consultation_fee }} ({{ selectedAppt.payment_status || 'Pending' }})</span>
                </div>
              </div>
            </div>

          </div>

          <!-- Modal Footer -->
          <div class="modal-footer">
            <button class="btn-modal-close" @click="closeApptModal">Close Dossier</button>
          </div>
        </div>
      </div>

    </div>
  </main>
</template>

<style scoped>
.rec-patients-page {
  min-height: 100vh;
  background: #f8fafc;
  padding: 32px 24px;
  color: #0f172a;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
.rec-shell {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.page-head .eyebrow {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: #059669;
  text-transform: uppercase;
  margin-bottom: 4px;
}
.page-head h1 {
  font-size: 30px;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
  letter-spacing: -0.02em;
}
.page-head h1 span { color: #059669; }
.head-sub { color: #64748b; font-size: 14px; margin: 6px 0 0; }

/* Grid Layout */
.layout-grid {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 20px;
  align-items: start;
}
@media (max-width: 900px) {
  .layout-grid { grid-template-columns: 1fr; }
}

/* Left Pane */
.left-pane { display: flex; flex-direction: column; gap: 14px; }
.search-box-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 14px;
}
.input-row { display: flex; gap: 8px; flex-wrap: wrap; }
.search-text-input {
  flex: 1;
  min-width: 160px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 13px;
  outline: none;
}
.search-phone-input {
  width: 90px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 13px;
  outline: none;
}
.btn-search {
  background: #059669;
  color: #ffffff;
  border: none;
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}
.patient-list-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  overflow: hidden;
  max-height: 75vh;
  display: flex;
  flex-direction: column;
}
.list-head {
  padding: 12px 14px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
}
.count-badge { font-size: 12px; font-weight: 700; color: #475569; }
.patients-scroll-list {
  overflow-y: auto;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.patient-list-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 10px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s;
}
.patient-list-item:hover { background: #f8fafc; }
.patient-list-item.active {
  background: #ecfdf5;
  border-color: #a7f3d0;
}
.item-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #e2e8f0;
  color: #0f172a;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 14px;
  flex-shrink: 0;
}
.patient-list-item.active .item-avatar {
  background: #059669;
  color: #ffffff;
}
.item-body { flex: 1; min-width: 0; }
.item-name { font-weight: 700; font-size: 13px; color: #0f172a; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.item-meta { font-size: 11px; color: #64748b; margin-top: 2px; }
.item-stats-chips { display: flex; gap: 4px; margin-top: 4px; }
.chip { font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; }
.chip-visits { background: #f1f5f9; color: #475569; }
.chip-up { background: #dbeafe; color: #1d4ed8; }
.arrow-indicator { color: #94a3b8; font-size: 14px; }
.patient-list-item.active .arrow-indicator { color: #059669; }
.loading-state, .empty-list { padding: 32px 16px; text-align: center; color: #64748b; font-size: 13px; }

/* Right Pane */
.placeholder-card {
  background: #ffffff;
  border: 1px dashed #cbd5e1;
  border-radius: 16px;
  padding: 60px 24px;
  text-align: center;
  color: #64748b;
}
.placeholder-icon { font-size: 48px; margin-bottom: 12px; }
.placeholder-card h3 { font-size: 18px; font-weight: 700; color: #0f172a; margin: 0 0 6px; }

/* Record Container */
.record-container { display: flex; flex-direction: column; gap: 16px; }
.patient-profile-banner {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 20px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 20px;
}
.banner-avatar {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: #059669;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 800;
  flex-shrink: 0;
}
.banner-info { flex: 1; min-width: 200px; }
.banner-info h2 { font-size: 20px; font-weight: 800; color: #0f172a; margin: 0 0 4px; }
.banner-sub { font-size: 13px; color: #64748b; }
.profile-stats-grid {
  display: flex;
  gap: 16px;
  background: #f8fafc;
  padding: 10px 16px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}
.pstat { display: flex; flex-direction: column; gap: 2px; text-align: center; }
.pstat span { font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; }
.pstat strong { font-size: 18px; font-weight: 800; color: #0f172a; }

/* Tab buttons */
.record-tabs {
  display: flex;
  gap: 8px;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 8px;
  overflow-x: auto;
}
.tab-btn {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 9px 16px;
  font-size: 13px;
  font-weight: 700;
  color: #64748b;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
}
.tab-btn:hover { background: #f1f5f9; color: #0f172a; }
.tab-btn.active {
  background: #059669;
  color: #ffffff;
  border-color: #059669;
}

/* Tab content */
.tab-content { display: flex; flex-direction: column; gap: 20px; }
.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 800;
  color: #0f172a;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin: 0 0 12px;
}
.title-dot { width: 8px; height: 8px; border-radius: 50%; }
.title-dot.blue { background: #2563eb; }
.title-dot.gray { background: #64748b; }
.empty-sub {
  background: #ffffff;
  border: 1px dashed #e2e8f0;
  border-radius: 12px;
  padding: 24px;
  text-align: center;
  color: #64748b;
  font-size: 13px;
}
.appt-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 12px;
}
.appt-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.appt-card--upcoming { border-left: 4px solid #2563eb; }
.appt-card--past { border-left: 4px solid #64748b; }
.appt-top { display: flex; justify-content: space-between; align-items: flex-start; }
.appt-date { font-size: 12px; font-weight: 700; color: #0f172a; }
.appt-doctor { font-size: 13px; font-weight: 700; color: #059669; }
.status-pill { font-size: 10px; font-weight: 800; padding: 2px 8px; border-radius: 6px; text-transform: uppercase; }
.status-upcoming { background: #dbeafe; color: #1e40af; }
.status-past { background: #f1f5f9; color: #475569; }
.diagnosis-highlight {
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  padding: 8px 10px;
  border-radius: 8px;
  font-size: 12px;
  color: #065f46;
}
.appt-reason, .appt-symptoms { font-size: 12px; color: #475569; }
.appt-footer { display: flex; gap: 8px; align-items: center; margin-top: 4px; font-size: 11px; }
.token-badge { background: #0f172a; color: #ffffff; padding: 2px 6px; border-radius: 4px; font-weight: 800; }
.checked-in-text { color: #059669; font-weight: 700; }
.not-checked-text { color: #64748b; }

/* Prescriptions */
.prescriptions-stack { display: flex; flex-direction: column; gap: 14px; }
.prescription-box {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.prescription-box.is-running { border-color: #a7f3d0; box-shadow: 0 2px 10px rgba(5,150,105,0.05); }
.prx-header { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px; }
.prx-title { font-size: 15px; font-weight: 800; color: #0f172a; display: flex; align-items: center; gap: 8px; }
.running-pill { background: #dcfce7; color: #166534; font-size: 10px; font-weight: 800; padding: 2px 8px; border-radius: 6px; }
.completed-pill { background: #f1f5f9; color: #64748b; font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 6px; }
.prx-meta { font-size: 12px; color: #64748b; margin-top: 2px; }
.prx-dx { background: #f0fdfa; border: 1px solid #ccfbf1; padding: 6px 10px; border-radius: 8px; font-size: 12px; color: #0f766e; }
.prx-meds-table-wrap { overflow-x: auto; }
.meds-table { width: 100%; border-collapse: collapse; font-size: 12px; text-align: left; }
.meds-table th { background: #f8fafc; padding: 8px 10px; color: #64748b; font-size: 11px; text-transform: uppercase; }
.meds-table td { padding: 8px 10px; border-top: 1px solid #f1f5f9; }
.freq-tag { background: #f0fdf4; color: #166534; font-weight: 700; padding: 2px 6px; border-radius: 4px; }
.prx-instructions { background: #f8fafc; padding: 10px; border-radius: 8px; font-size: 12px; color: #475569; display: flex; flex-direction: column; gap: 4px; }

/* History & Reports Cards */
.history-grid, .reports-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 12px;
}
.history-card, .report-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
}
.h-top, .r-top { display: flex; justify-content: space-between; align-items: flex-start; }
.h-top h4, .r-top h4 { margin: 0; font-size: 14px; font-weight: 700; color: #0f172a; }
.severity-pill { font-size: 10px; font-weight: 800; padding: 2px 6px; border-radius: 4px; text-transform: uppercase; }
.sev-high, .sev-severe { background: #fee2e2; color: #b91c1c; }
.sev-moderate { background: #fef3c7; color: #b45309; }
.sev-mild { background: #ecfdf5; color: #047857; }
.r-type { font-size: 11px; color: #64748b; }
.r-status { font-size: 10px; font-weight: 800; padding: 2px 6px; border-radius: 4px; }
.r-status--completed { background: #dcfce7; color: #166534; }
.r-status--pending { background: #fef3c7; color: #92400e; }
.btn-file-link { color: #2563eb; font-weight: 700; text-decoration: none; margin-top: 4px; }
.btn-file-link:hover { text-decoration: underline; }

/* Clickable appointment card */
.appt-card.clickable {
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}
.appt-card.clickable:hover {
  transform: translateY(-2px);
  border-color: #0d9488;
  box-shadow: 0 8px 20px -4px rgba(13, 148, 136, 0.15);
}
.appt-click-hint {
  margin-left: auto;
  color: #0d9488;
  font-weight: 700;
  font-size: 11px;
}
.appt-card.clickable:hover .appt-click-hint {
  text-decoration: underline;
}

/* Appointment Dossier Modal */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 24px;
}
.modal-card {
  background: #ffffff;
  border-radius: 20px;
  width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 25px 50px -12px rgba(15, 23, 42, 0.25);
  overflow: hidden;
  border: 1px solid #e2e8f0;
}
.modal-card--lg {
  max-width: 860px;
}
.modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 24px 28px 18px;
  border-bottom: 1px solid #f1f5f9;
  background: #ffffff;
}
.modal-eyebrow-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}
.modal-eyebrow {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: #0d9488;
  text-transform: uppercase;
}
.fast-track-pill {
  background: #fef08a;
  color: #854d0e;
  font-size: 10px;
  font-weight: 800;
  padding: 2px 7px;
  border-radius: 6px;
}
.modal-headline {
  font-size: 20px;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
}
.modal-datetime {
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
  margin-top: 4px;
}
.modal-close-btn {
  background: #f1f5f9;
  border: none;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.modal-close-btn:hover {
  background: #e2e8f0;
  color: #0f172a;
}
.modal-body {
  padding: 24px 28px;
  overflow-y: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.detail-loading-banner {
  background: #f0fdfa;
  border: 1px solid #ccfbf1;
  color: #0f766e;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.loader-spinner-sm {
  width: 14px;
  height: 14px;
  border: 2px solid #0f766e;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.modal-error-banner {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 12px;
}

/* Dossier People Grid */
.dossier-people-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 14px;
}
.dossier-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 16px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.dossier-card.doctor-side {
  border-left: 4px solid #0d9488;
}
.dossier-card.patient-side {
  border-left: 4px solid #2563eb;
}
.dc-icon {
  font-size: 24px;
  line-height: 1;
}
.dc-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.dc-label {
  font-size: 10px;
  font-weight: 800;
  text-transform: uppercase;
  color: #64748b;
  letter-spacing: 0.05em;
}
.dc-name {
  font-size: 14px;
  font-weight: 800;
  color: #0f172a;
}
.dc-sub {
  font-size: 12px;
  color: #64748b;
}
.dc-contact {
  font-size: 11px;
  color: #475569;
  margin-top: 2px;
}

/* Dossier Section */
.dossier-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.dossier-title {
  font-size: 13px;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.dossier-count {
  font-size: 11px;
  color: #0d9488;
  font-weight: 700;
}
.dossier-empty {
  font-size: 12px;
  color: #94a3b8;
  font-style: italic;
  padding: 12px 14px;
  background: #f8fafc;
  border-radius: 10px;
  border: 1px dashed #e2e8f0;
}

/* Clinical Grid */
.dossier-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}
.dossier-item {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.dossier-item.span-full {
  grid-column: 1 / -1;
}
.dossier-item.diagnosis-item {
  background: #ecfdf5;
  border-color: #a7f3d0;
}
.dossier-item.followup-item {
  background: #eff6ff;
  border-color: #bfdbfe;
}
.dossier-item-label {
  font-size: 10px;
  font-weight: 800;
  text-transform: uppercase;
  color: #64748b;
  letter-spacing: 0.05em;
}
.dossier-item-value {
  font-size: 13px;
  color: #1e293b;
}
.diagnosis-val {
  font-weight: 700;
  color: #065f46;
  font-size: 14px;
}
.pre-wrap {
  white-space: pre-wrap;
  line-height: 1.5;
}

/* Modal Prescriptions */
.modal-prx-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.modal-prx-item {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.modal-prx-item-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* Modal Reports */
.modal-reports-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 12px;
}

/* Queue Meta Grid */
.queue-meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px;
}
.qmeta-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.qmeta-label {
  font-size: 10px;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
}
.qmeta-val {
  font-size: 12px;
  font-weight: 700;
  color: #0f172a;
}
.capitalize {
  text-transform: capitalize;
}

/* Modal Footer */
.modal-footer {
  padding: 16px 28px;
  border-top: 1px solid #f1f5f9;
  display: flex;
  justify-content: flex-end;
  background: #f8fafc;
}
.btn-modal-close {
  background: #0f172a;
  color: #ffffff;
  font-weight: 700;
  font-size: 13px;
  padding: 8px 18px;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  transition: background 0.15s ease;
}
.btn-modal-close:hover {
  background: #1e293b;
}
</style>
