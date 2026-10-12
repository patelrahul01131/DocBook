<script setup>
import { ref, onMounted, computed } from 'vue'
import { Button } from 'frappe-ui'
import { useRouter } from 'vue-router'
import { call } from '../../api'

const router = useRouter()

const patients = ref([])
const appointments = ref([])
const loading = ref(false)
const refreshing = ref(false)
const error = ref(null)
const searchQuery = ref('')

// Patient Detail Drawer / Modal
const selectedPatient = ref(null)
const patientHistory = ref([])
const patientPrescriptions = ref([])
const historyLoading = ref(false)
const activeDetailTab = ref('history')

const filteredPatients = computed(() => {
  const q = searchQuery.value.toLowerCase().trim()
  if (!q) return patients.value
  return patients.value.filter(p =>
    (p.full_name || '').toLowerCase().includes(q) ||
    (p.phone || '').includes(q) ||
    (p.user || '').toLowerCase().includes(q)
  )
})

async function fetchData(isRefresh = false) {
  if (isRefresh) {
    refreshing.value = true
  } else {
    loading.value = true
  }
  error.value = null

  try {
    const [pRes, aRes] = await Promise.all([
      call('docbook.api.prescription.get_doctor_patients'),
      call('docbook.api.prescription.get_doctor_appointments'),
    ])
    patients.value = Array.isArray(pRes) ? pRes : []
    appointments.value = Array.isArray(aRes) ? aRes : []
  } catch (e) {
    error.value = e.message || 'Unable to load patients.'
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

function getPatientAppointments(patientName) {
  return appointments.value.filter(a => a.patient === patientName)
}

function lastVisit(patientName) {
  const appts = getPatientAppointments(patientName)
  if (!appts.length) return null
  const sorted = [...appts].sort((a, b) =>
    new Date(`${b.appointment_date} ${b.appointment_time || ''}`) -
    new Date(`${a.appointment_date} ${a.appointment_time || ''}`)
  )
  return sorted[0].appointment_date
}

async function selectPatient(patient) {
  selectedPatient.value = patient
  historyLoading.value = true
  patientHistory.value = []
  patientPrescriptions.value = []
  activeDetailTab.value = 'history'

  try {
    const [hRes, pRes] = await Promise.all([
      call('docbook.api.medical_history.get_patient_medical_history', { patient: patient.name }),
      call('docbook.api.prescription.get_doctor_prescriptions').catch(() => []),
    ])
    patientHistory.value = Array.isArray(hRes) ? hRes : []
    if (Array.isArray(pRes)) {
      patientPrescriptions.value = pRes.filter(p => p.patient === patient.name)
    }
  } catch {
    patientHistory.value = []
  } finally {
    historyLoading.value = false
  }
}

function closePatientDetail() {
  selectedPatient.value = null
}

function formatDate(d) {
  if (!d) return '—'
  return new Date(`${d}T00:00:00`).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
}

function getInitials(name) {
  if (!name) return 'PT'
  return name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()
}

onMounted(() => {
  fetchData()
})
</script>

<template>
  <main class="doctor-patients-page">
    <div class="patients-shell">

      <!-- Header -->
      <header class="page-header">
        <div class="header-copy">
          <div class="eyebrow">
            <span class="lucide-users"></span>
            DOCTOR PORTAL
          </div>
          <h1>My Patients<span>.</span></h1>
          <p>
            Patients registered under your medical care, comprehensive records, and prescription histories.
          </p>
        </div>

        <div class="header-actions">
          <Button
            label="Doctor Dashboard"
            icon-left="lucide-layout-dashboard"
            @click="router.push('/doctor')"
          />
          <Button
            label="Refresh"
            icon-left="lucide-refresh-cw"
            :loading="refreshing"
            :disabled="loading || refreshing"
            @click="fetchData(true)"
          />
        </div>
      </header>

      <!-- Error State -->
      <div v-if="error" class="error-banner">
        <span>⚠️</span>
        <div class="flex-1 text-sm">{{ error }}</div>
        <Button label="Retry" @click="fetchData(false)" />
      </div>

      <!-- Stats Grid -->
      <section class="stats-grid">
        <article class="stat-card">
          <div class="stat-icon blue">
            <span class="lucide-users"></span>
          </div>
          <p>Total Patients</p>
          <h2>{{ loading ? '—' : patients.length }}</h2>
          <span class="stat-caption">Registered in your practice</span>
        </article>

        <article class="stat-card">
          <div class="stat-icon teal">
            <span class="lucide-calendar-days"></span>
          </div>
          <p>Consultations</p>
          <h2>{{ loading ? '—' : appointments.length }}</h2>
          <span class="stat-caption">Total appointment sessions</span>
        </article>

        <article class="stat-card">
          <div class="stat-icon purple">
            <span class="lucide-check-circle-2"></span>
          </div>
          <p>Completed Visits</p>
          <h2>{{ loading ? '—' : appointments.filter(a => a.status === 'Completed').length }}</h2>
          <span class="stat-caption">Finished treatments</span>
        </article>
      </section>

      <!-- Search Bar -->
      <div class="search-row">
        <div class="search-box">
          <span class="lucide-search search-icon"></span>
          <input
            v-model="searchQuery"
            type="text"
            class="search-input"
            placeholder="Search patient by name, phone, or email..."
          />
          <button v-if="searchQuery" class="clear-btn" @click="searchQuery = ''">✕</button>
        </div>
      </div>

      <!-- Patients Grid -->
      <div v-if="loading" class="patients-grid">
        <div v-for="i in 3" :key="i" class="card-skeleton"></div>
      </div>

      <div v-else-if="!filteredPatients.length" class="empty-state">
        <div class="empty-icon">
          <span class="lucide-user-x"></span>
        </div>
        <h3>No patients found</h3>
        <p v-if="searchQuery">No patients matched "{{ searchQuery }}".</p>
        <p v-else>You have not conducted appointments with any patients yet.</p>
      </div>

      <div v-else class="patients-grid">
        <article
          v-for="p in filteredPatients"
          :key="p.name"
          class="patient-card"
        >
          <div class="card-top">
            <div class="avatar-box">
              {{ getInitials(p.full_name) }}
            </div>
            <div class="patient-main">
              <h3 class="patient-name">{{ p.full_name }}</h3>
              <div class="patient-sub">
                <span v-if="p.age">{{ p.age }} yrs</span>
                <span v-if="p.gender">• {{ p.gender }}</span>
              </div>
            </div>
          </div>

          <!-- Contact info strip -->
          <div class="info-strip">
            <div v-if="p.phone" class="info-item">
              <span class="lucide-phone"></span>
              <span>{{ p.phone }}</span>
            </div>
            <div v-if="p.user" class="info-item">
              <span class="lucide-mail"></span>
              <span class="truncate">{{ p.user }}</span>
            </div>
          </div>

          <!-- Visit Summary -->
          <div class="visit-summary">
            <div class="visit-stat">
              <span class="v-label">Total Visits</span>
              <span class="v-val">{{ getPatientAppointments(p.name).length }}</span>
            </div>
            <div class="visit-stat">
              <span class="v-label">Last Consult</span>
              <span class="v-val">{{ formatDate(lastVisit(p.name)) }}</span>
            </div>
          </div>

          <!-- Card Actions -->
          <div class="card-actions">
            <button
              class="btn-primary"
              @click="selectPatient(p)"
            >
              <span class="lucide-clipboard-list"></span>
              Medical Records
            </button>
          </div>
        </article>
      </div>

    </div>

    <!-- Patient Detailed Records Modal -->
    <div v-if="selectedPatient" class="modal-backdrop" @click.self="closePatientDetail">
      <div class="modal-card">
        <div class="modal-header">
          <div class="flex items-center gap-3">
            <div class="avatar-small">
              {{ getInitials(selectedPatient.full_name) }}
            </div>
            <div>
              <h3>{{ selectedPatient.full_name }}</h3>
              <p class="text-xs text-slate-500">
                {{ selectedPatient.age ? `${selectedPatient.age} yrs • ` : '' }}
                {{ selectedPatient.gender || '' }} •
                {{ selectedPatient.phone || 'No phone' }}
              </p>
            </div>
          </div>
          <button class="close-btn" @click="closePatientDetail">✕</button>
        </div>

        <!-- Modal Tabs -->
        <div class="modal-tabs">
          <button
            class="m-tab"
            :class="{ active: activeDetailTab === 'history' }"
            @click="activeDetailTab = 'history'"
          >
            Medical Conditions & History ({{ patientHistory.length }})
          </button>
          <button
            class="m-tab"
            :class="{ active: activeDetailTab === 'prescriptions' }"
            @click="activeDetailTab = 'prescriptions'"
          >
            Prescriptions ({{ patientPrescriptions.length }})
          </button>
        </div>

        <div class="modal-body">
          <div v-if="historyLoading" class="text-center py-8 text-sm text-slate-500">
            Loading patient records...
          </div>

          <!-- History Tab -->
          <div v-else-if="activeDetailTab === 'history'">
            <div v-if="!patientHistory.length" class="empty-state small">
              <p>No chronic conditions or allergies logged for this patient.</p>
            </div>
            <div v-else class="space-y-3">
              <div
                v-for="item in patientHistory"
                :key="item.name"
                class="record-card"
              >
                <div class="flex items-center justify-between mb-1">
                  <span class="font-bold text-slate-800 text-sm">{{ item.condition_name || item.record_type }}</span>
                  <span
                    class="text-[11px] px-2 py-0.5 rounded-full font-semibold"
                    :class="item.status === 'Active' ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'"
                  >
                    {{ item.status }}
                  </span>
                </div>
                <p v-if="item.description" class="text-xs text-slate-600 mb-1">{{ item.description }}</p>
                <div class="text-[11px] text-slate-400 flex gap-4">
                  <span v-if="item.severity">Severity: {{ item.severity }}</span>
                  <span v-if="item.date_of_diagnosis">Diagnosed: {{ formatDate(item.date_of_diagnosis) }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Prescriptions Tab -->
          <div v-else-if="activeDetailTab === 'prescriptions'">
            <div v-if="!patientPrescriptions.length" class="empty-state small">
              <p>No prescriptions issued by you for this patient yet.</p>
            </div>
            <div v-else class="space-y-3">
              <div
                v-for="prx in patientPrescriptions"
                :key="prx.name"
                class="record-card"
              >
                <div class="flex items-center justify-between mb-1">
                  <span class="font-bold text-slate-800 text-sm">
                    Prescription #{{ prx.name }}
                  </span>
                  <span class="text-[11px] px-2 py-0.5 rounded-full font-semibold bg-blue-100 text-blue-800">
                    {{ prx.status }}
                  </span>
                </div>
                <p v-if="prx.diagnosis" class="text-xs text-slate-700 mb-1">
                  <strong>Diagnosis:</strong> {{ prx.diagnosis }}
                </p>
                <div class="text-[11px] text-slate-400 flex gap-4">
                  <span>Date: {{ formatDate(prx.prescription_date) }}</span>
                  <span v-if="prx.follow_up_date">Follow-up: {{ formatDate(prx.follow_up_date) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <Button label="Close" @click="closePatientDetail" />
        </div>
      </div>
    </div>

  </main>
</template>

<style scoped>
.doctor-patients-page {
  min-height: 100vh;
  padding: 32px 32px 64px;
  background:
    radial-gradient(circle at 10% 8%, rgba(13, 148, 136, 0.08), transparent 32%),
    radial-gradient(circle at 90% 12%, rgba(37, 99, 235, 0.06), transparent 30%),
    #f4f7fb;
  color: #0f172a;
}

.patients-shell {
  max-width: 1200px;
  margin: 0 auto;
}

/* Header */
.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 32px;
  padding-bottom: 24px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.8);
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 1.2px;
  text-transform: uppercase;
  color: #0d9488;
  margin-bottom: 8px;
}

.header-copy h1 {
  font-size: clamp(28px, 3.5vw, 40px);
  font-weight: 800;
  letter-spacing: -1.2px;
  margin: 0 0 8px;
  color: #0f172a;
}

.header-copy h1 span { color: #0d9488; }
.header-copy p { font-size: 15px; color: #64748b; margin: 0; max-width: 600px; }

.header-actions { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 32px;
}

.stat-card {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.9);
  border-radius: 20px;
  padding: 22px 20px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  margin-bottom: 14px;
}

.stat-icon.blue   { background: rgba(37, 99, 235, 0.12); color: #2563eb; }
.stat-icon.teal   { background: rgba(13, 148, 136, 0.12); color: #0d9488; }
.stat-icon.purple { background: rgba(124, 58, 237, 0.12); color: #7c3aed; }

.stat-card p { font-size: 13px; color: #64748b; margin: 0 0 6px; font-weight: 500; }
.stat-card h2 { font-size: 32px; font-weight: 800; letter-spacing: -1px; margin: 0; color: #0f172a; }
.stat-caption { display: block; font-size: 11px; color: #94a3b8; margin-top: 6px; }

/* Search */
.search-row { margin-bottom: 28px; }
.search-box {
  position: relative;
  display: flex;
  align-items: center;
  max-width: 480px;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.03);
}

.search-icon { margin-left: 14px; font-size: 16px; color: #94a3b8; }
.search-input {
  flex: 1;
  padding: 12px 14px;
  border: none;
  background: transparent;
  font-size: 14px;
  outline: none;
  color: #0f172a;
}
.clear-btn { padding: 6px 12px; background: none; border: none; color: #94a3b8; cursor: pointer; }

/* Patients Grid */
.patients-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.patient-card {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 20px;
  padding: 22px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
  display: flex;
  flex-direction: column;
  gap: 16px;
  transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
}

.patient-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 36px rgba(15, 23, 42, 0.08);
  border-color: rgba(13, 148, 136, 0.4);
}

.card-top {
  display: flex;
  align-items: center;
  gap: 12px;
}

.avatar-box {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: linear-gradient(135deg, #0d9488 0%, #2563eb 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  font-weight: 800;
  box-shadow: 0 4px 12px rgba(13, 148, 136, 0.2);
  flex-shrink: 0;
}

.patient-name {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 2px;
}

.patient-sub {
  font-size: 12px;
  color: #64748b;
  display: flex;
  gap: 5px;
}

/* Info Strip */
.info-strip {
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: #f8fafc;
  padding: 10px 12px;
  border-radius: 12px;
  font-size: 12px;
  color: #475569;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Visit Summary */
.visit-summary {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  padding-top: 4px;
}

.visit-stat {
  display: flex;
  flex-direction: column;
}

.v-label {
  font-size: 11px;
  color: #94a3b8;
  font-weight: 500;
}

.v-val {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}

/* Card Actions */
.card-actions {
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid #f1f5f9;
}

.btn-primary {
  width: 100%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 9px 16px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 700;
  background: #0d9488;
  color: white;
  border: none;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-primary:hover {
  background: #0f766e;
  box-shadow: 0 4px 12px rgba(13, 148, 136, 0.25);
}

/* Modal */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-card {
  background: white;
  border-radius: 20px;
  width: 100%;
  max-width: 580px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 24px 64px rgba(15, 23, 42, 0.2);
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid #f1f5f9;
}

.avatar-small {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: #0d9488;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 800;
}

.modal-header h3 { font-size: 16px; font-weight: 800; color: #0f172a; margin: 0; }
.close-btn { background: none; border: none; font-size: 16px; color: #94a3b8; cursor: pointer; }

.modal-tabs {
  display: flex;
  border-bottom: 1px solid #e2e8f0;
  padding: 0 24px;
  gap: 16px;
}

.m-tab {
  padding: 12px 0;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  margin-bottom: -1px;
}

.m-tab.active {
  color: #0d9488;
  border-bottom-color: #0d9488;
}

.modal-body {
  padding: 20px 24px;
  overflow-y: auto;
  flex: 1;
}

.record-card {
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid #f1f5f9;
  display: flex;
  justify-content: flex-end;
}

/* Empty & Skeleton */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 48px 24px;
  background: white;
  border: 1px dashed #cbd5e1;
  border-radius: 20px;
}
.empty-state.small { padding: 24px; }
.empty-icon {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  background: #f0fdfa;
  color: #0d9488;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  margin-bottom: 16px;
}

.card-skeleton {
  height: 220px;
  background: white;
  border-radius: 20px;
  animation: pulse 1.5s infinite;
}

@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }

@media (max-width: 768px) {
  .stats-grid { grid-template-columns: 1fr; }
  .patients-grid { grid-template-columns: 1fr; }
}
</style>
