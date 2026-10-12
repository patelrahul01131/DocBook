<script setup>
import { ref, onMounted, computed, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { Button } from 'frappe-ui'
import { call } from '../../api'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const appointments = ref([])
const loading = ref(false)
const refreshing = ref(false)
const error = ref(null)
const activeTab = ref('all')
const searchQuery = ref('')
const updatingStatus = ref(null)

// History modal
const showHistoryModal = ref(false)
const selectedPatient = ref(null)
const patientHistory = ref([])
const historyLoading = ref(false)

// Create Appointment Modal
const showCreateModal = ref(false)
const creatingAppt = ref(false)
const createError = ref('')
const allPatients = ref([])
const createForm = reactive({
  patient: '',
  appointment_date: '',
  appointment_time: '10:00:00',
  reason: '',
  symptoms: '',
})

// Edit Appointment Modal
const showEditModal = ref(false)
const editingAppt = ref(false)
const editError = ref('')
const editForm = reactive({
  name: '',
  patient_name: '',
  appointment_date: '',
  appointment_time: '',
  reason: '',
  symptoms: '',
})

// Delete Appointment Modal
const showDeleteModal = ref(false)
const deletingAppt = ref(false)
const deleteError = ref('')
const selectedForDelete = ref(null)

const doctorEmail = computed(() => {
  const user = auth.user || auth.currentUser || null
  return String(user?.email || user?.name || '').trim().toLowerCase()
})

const todayStr = computed(() => {
  const d = new Date()
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
})

async function fetchPatients() {
  try {
    const res = await call('docbook.api.prescription.get_all_patients')
    allPatients.value = Array.isArray(res) ? res : []
  } catch {
    try {
      const fallback = await call('docbook.api.prescription.get_doctor_patients')
      allPatients.value = Array.isArray(fallback) ? fallback : []
    } catch {
      allPatients.value = []
    }
  }
}

function openCreateModal() {
  createError.value = ''
  createForm.patient = allPatients.value[0]?.name || ''
  createForm.appointment_date = todayStr.value
  createForm.appointment_time = '10:00:00'
  createForm.reason = ''
  createForm.symptoms = ''
  showCreateModal.value = true
  if (!allPatients.value.length) {
    fetchPatients()
  }
}

async function handleCreateAppointment() {
  if (!createForm.patient) {
    createError.value = 'Please select a patient.'
    return
  }
  if (!createForm.appointment_date || !createForm.appointment_time) {
    createError.value = 'Please select a date and time.'
    return
  }

  creatingAppt.value = true
  createError.value = ''

  try {
    await call('docbook.api.appointment.create_appointment', {
      patient: createForm.patient,
      doctor: doctorEmail.value,
      appointment_date: createForm.appointment_date,
      appointment_time: createForm.appointment_time.length === 5 ? `${createForm.appointment_time}:00` : createForm.appointment_time,
      reason: createForm.reason,
      symptoms: createForm.symptoms,
    })
    showCreateModal.value = false
    await fetchAppointments(true)
  } catch (err) {
    createError.value = err.message || 'Failed to create appointment.'
  } finally {
    creatingAppt.value = false
  }
}

function openEditModal(appt) {
  editError.value = ''
  editForm.name = appt.name
  editForm.patient_name = appt.patient_name || appt.patient || 'Patient'
  editForm.appointment_date = appt.appointment_date || ''
  editForm.appointment_time = (appt.appointment_time || '').slice(0, 5) || '10:00'
  editForm.reason = appt.reason || ''
  editForm.symptoms = appt.symptoms || ''
  showEditModal.value = true
}

async function handleEditAppointment() {
  if (!editForm.name) return
  editingAppt.value = true
  editError.value = ''

  try {
    const formattedTime = editForm.appointment_time.length === 5 ? `${editForm.appointment_time}:00` : editForm.appointment_time
    await call('docbook.api.appointment.update_appointment', {
      appointment_id: editForm.name,
      appointment_date: editForm.appointment_date,
      appointment_time: formattedTime,
      reason: editForm.reason,
      symptoms: editForm.symptoms,
    })
    showEditModal.value = false
    await fetchAppointments(true)
  } catch (err) {
    editError.value = err.message || 'Failed to update appointment.'
  } finally {
    editingAppt.value = false
  }
}

function openDeleteModal(appt) {
  deleteError.value = ''
  selectedForDelete.value = appt
  showDeleteModal.value = true
}

async function handleDeleteAppointment() {
  if (!selectedForDelete.value) return
  deletingAppt.value = true
  deleteError.value = ''

  try {
    await call('docbook.api.appointment.delete_appointment', {
      appointment_id: selectedForDelete.value.name,
    })
    showDeleteModal.value = false
    selectedForDelete.value = null
    await fetchAppointments(true)
  } catch (err) {
    deleteError.value = err.message || 'Failed to delete appointment.'
  } finally {
    deletingAppt.value = false
  }
}

const tabs = [
  { key: 'all', label: 'All' },
  { key: 'today', label: 'Today' },
  { key: 'Pending', label: 'Pending' },
  { key: 'Confirmed', label: 'Confirmed' },
  { key: 'Completed', label: 'Completed' },
  { key: 'Cancelled', label: 'Cancelled' },
]

const filteredAppointments = computed(() => {
  let list = appointments.value

  if (activeTab.value === 'today') {
    list = list.filter(a => a.appointment_date === todayStr.value)
  } else if (activeTab.value !== 'all') {
    list = list.filter(a => a.status === activeTab.value)
  }

  const q = searchQuery.value.toLowerCase().trim()
  if (q) {
    list = list.filter(a =>
      (a.patient_name || '').toLowerCase().includes(q) ||
      (a.reason || '').toLowerCase().includes(q) ||
      (a.patient_phone || '').includes(q) ||
      (a.diagnosis || '').toLowerCase().includes(q)
    )
  }

  return list
})

async function fetchAppointments(isRefresh = false) {
  if (isRefresh) {
    refreshing.value = true
  } else {
    loading.value = true
  }
  error.value = null

  try {
    const res = await call('docbook.api.prescription.get_doctor_appointments')
    appointments.value = Array.isArray(res) ? res : []
  } catch (e) {
    error.value = e.message || 'Unable to load doctor appointments.'
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

async function updateStatus(appointmentName, newStatus) {
  updatingStatus.value = appointmentName
  try {
    await call('docbook.api.appointment.update_appointment_status', {
      appointment_id: appointmentName,
      status: newStatus,
    })
    const found = appointments.value.find(a => a.name === appointmentName)
    if (found) {
      found.status = newStatus
    }
  } catch (err) {
    alert(err.message || 'Failed to update status')
  } finally {
    updatingStatus.value = null
  }
}

function openConsultation(appt) {
  router.push(`/consultation/${appt.name}`)
}

async function viewPatientHistory(appt) {
  selectedPatient.value = appt
  showHistoryModal.value = true
  historyLoading.value = true
  patientHistory.value = []
  try {
    const res = await call('docbook.api.medical_history.get_patient_medical_history', {
      patient: appt.patient,
    })
    patientHistory.value = Array.isArray(res) ? res : []
  } catch {
    patientHistory.value = []
  } finally {
    historyLoading.value = false
  }
}

function formatDate(d) {
  if (!d) return '—'
  return new Date(`${d}T00:00:00`).toLocaleDateString('en-IN', {
    weekday: 'short', day: 'numeric', month: 'short', year: 'numeric',
  })
}

function formatTime(t) {
  if (!t) return '—'
  const [h, m] = t.split(':')
  const hour = parseInt(h, 10)
  const ampm = hour >= 12 ? 'PM' : 'AM'
  const displayHour = hour % 12 || 12
  return `${displayHour}:${m} ${ampm}`
}

function formatFee(fee) {
  if (!fee) return 'Free'
  return `₹${Number(fee).toLocaleString('en-IN')}`
}

function getInitials(name) {
  if (!name) return 'PT'
  return name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()
}

function tabCount(key) {
  if (key === 'all') return appointments.value.length
  if (key === 'today') return appointments.value.filter(a => a.appointment_date === todayStr.value).length
  return appointments.value.filter(a => a.status === key).length
}

onMounted(() => {
  fetchAppointments()
})
</script>

<template>
  <main class="doctor-appointments-page">
    <div class="appointments-shell">

      <!-- Header -->
      <header class="page-header">
        <div class="header-copy">
          <div class="eyebrow">
            <span class="lucide-calendar-check"></span>
            DOCTOR PORTAL
          </div>
          <h1>My Appointments<span>.</span></h1>
          <p>
            Complete list of patient appointments, clinical consultations, and history records.
          </p>
        </div>

        <div class="header-actions">
          <Button
            label="+ New Appointment"
            theme="green"
            variant="solid"
            icon-left="lucide-plus"
            @click="openCreateModal"
          />
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
            @click="fetchAppointments(true)"
          />
        </div>
      </header>

      <!-- Error State -->
      <div v-if="error" class="error-banner">
        <span>⚠️</span>
        <div class="flex-1 text-sm">{{ error }}</div>
        <Button label="Retry" @click="fetchAppointments(false)" />
      </div>

      <!-- Filter Controls: Search & Tabs -->
      <div class="controls-row">
        <!-- Search input -->
        <div class="search-box">
          <span class="lucide-search search-icon"></span>
          <input
            v-model="searchQuery"
            type="text"
            class="search-input"
            placeholder="Search by patient name, phone, diagnosis..."
          />
          <button v-if="searchQuery" class="clear-btn" @click="searchQuery = ''">✕</button>
        </div>

        <!-- Filter Tabs -->
        <div class="filter-tabs">
          <button
            v-for="t in tabs"
            :key="t.key"
            class="tab-btn"
            :class="{ active: activeTab === t.key }"
            @click="activeTab = t.key"
          >
            {{ t.label }}
            <span class="tab-badge">{{ tabCount(t.key) }}</span>
          </button>
        </div>
      </div>

      <!-- Appointments List / Grid -->
      <div v-if="loading" class="appointment-grid">
        <div v-for="i in 4" :key="i" class="card-skeleton"></div>
      </div>

      <div v-else-if="!filteredAppointments.length" class="empty-state">
        <div class="empty-icon">
          <span class="lucide-calendar-x"></span>
        </div>
        <h3>No appointments found</h3>
        <p v-if="searchQuery">
          No appointments matched your search query "{{ searchQuery }}".
        </p>
        <p v-else>
          No appointments found in the "{{ activeTab }}" tab.
        </p>
        <button v-if="searchQuery" class="reset-btn" @click="searchQuery = ''">
          Clear Search
        </button>
      </div>

      <div v-else class="appointment-grid">
        <article
          v-for="appt in filteredAppointments"
          :key="appt.name"
          class="appointment-card"
        >
          <!-- Top Row -->
          <div class="card-top">
            <div class="patient-info">
              <div class="patient-avatar">
                {{ getInitials(appt.patient_name) }}
              </div>
              <div>
                <h3 class="patient-name">{{ appt.patient_name || 'Patient' }}</h3>
                <div class="patient-sub">
                  <span v-if="appt.age">{{ appt.age }} yrs</span>
                  <span v-if="appt.gender">• {{ appt.gender }}</span>
                  <span v-if="appt.patient_phone">• {{ appt.patient_phone }}</span>
                </div>
              </div>
            </div>

            <span
              class="status-tag"
              :class="`status-${(appt.status || 'pending').toLowerCase()}`"
            >
              {{ appt.status || 'Pending' }}
            </span>
          </div>

          <!-- Schedule Strip -->
          <div class="schedule-strip">
            <div class="strip-item">
              <span class="lucide-calendar"></span>
              <span>{{ formatDate(appt.appointment_date) }}</span>
            </div>
            <div class="strip-item">
              <span class="lucide-clock"></span>
              <strong>{{ formatTime(appt.appointment_time) }}</strong>
            </div>
            <div class="strip-item fee">
              <span>{{ formatFee(appt.consultation_fee) }}</span>
            </div>
          </div>

          <!-- Reason & Notes -->
          <div v-if="appt.reason" class="reason-box">
            <span class="reason-label">Chief Complaint:</span>
            <span class="reason-text">{{ appt.reason }}</span>
          </div>

          <!-- Clinical Record Preview -->
          <div v-if="appt.diagnosis || appt.symptoms" class="clinical-box">
            <div v-if="appt.diagnosis" class="diagnosis-row">
              <strong>Dx:</strong> {{ appt.diagnosis }}
            </div>
            <div v-if="appt.treatment_plan" class="plan-row">
              <strong>Rx Plan:</strong> {{ appt.treatment_plan }}
            </div>
          </div>

          <!-- Actions Footer -->
          <div class="card-actions">
            <button
              class="btn-primary"
              @click="openConsultation(appt)"
            >
              <span class="lucide-clipboard-pen-line"></span>
              Consult & Rx
            </button>

            <button
              class="btn-secondary"
              @click="viewPatientHistory(appt)"
              title="View Patient Medical History"
            >
              <span class="lucide-history"></span>
              History
            </button>

            <!-- Edit Button -->
            <button
              class="btn-secondary"
              @click="openEditModal(appt)"
              title="Edit appointment"
            >
              <span class="lucide-pencil"></span>
              Edit
            </button>

            <!-- Delete Button -->
            <button
              class="btn-danger-outline"
              @click="openDeleteModal(appt)"
              title="Delete appointment"
            >
              <span class="lucide-trash-2"></span>
              Delete
            </button>

            <!-- Quick Status Toggles -->
            <button
              v-if="appt.status === 'Pending'"
              class="btn-status-confirm"
              :disabled="updatingStatus === appt.name"
              @click="updateStatus(appt.name, 'Confirmed')"
            >
              ✓ Confirm
            </button>

            <button
              v-if="appt.status === 'Confirmed'"
              class="btn-status-complete"
              :disabled="updatingStatus === appt.name"
              @click="updateStatus(appt.name, 'Completed')"
            >
              ✓ Complete
            </button>

            <button
              v-if="['Pending', 'Confirmed'].includes(appt.status)"
              class="btn-status-cancel"
              :disabled="updatingStatus === appt.name"
              @click="updateStatus(appt.name, 'Cancelled')"
              title="Cancel appointment"
            >
              ✕
            </button>
          </div>
        </article>
      </div>

    </div>

    <!-- Patient Medical History Modal -->
    <div v-if="showHistoryModal" class="modal-backdrop" @click.self="showHistoryModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <div>
            <h3>Medical History: {{ selectedPatient?.patient_name || 'Patient' }}</h3>
            <p class="text-xs text-slate-500">Chronic conditions, allergies, and diagnoses</p>
          </div>
          <button class="close-btn" @click="showHistoryModal = false">✕</button>
        </div>

        <div class="modal-body">
          <div v-if="historyLoading" class="text-center py-6 text-sm text-slate-500">
            Loading medical history...
          </div>
          <div v-else-if="!patientHistory.length" class="empty-state small">
            <p>No medical history records logged for this patient.</p>
          </div>
          <div v-else class="space-y-3">
            <div
              v-for="item in patientHistory"
              :key="item.name"
              class="p-3 rounded-xl border border-slate-200 bg-slate-50/50"
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
              <div class="text-[11px] text-slate-400 flex gap-3">
                <span v-if="item.severity">Severity: {{ item.severity }}</span>
                <span v-if="item.date_of_diagnosis">Diagnosed: {{ formatDate(item.date_of_diagnosis) }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <Button label="Close" @click="showHistoryModal = false" />
        </div>
      </div>
    </div>

    <!-- Create Appointment Modal -->
    <div v-if="showCreateModal" class="modal-backdrop" @click.self="showCreateModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <div>
            <h3>Schedule New Appointment</h3>
            <p class="text-xs text-slate-500">Book visit for a patient</p>
          </div>
          <button class="close-btn" @click="showCreateModal = false">✕</button>
        </div>

        <div class="modal-body space-y-4">
          <div v-if="createError" class="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl">
            {{ createError }}
          </div>

          <div>
            <label class="block text-xs font-bold text-slate-700 mb-1">Select Patient *</label>
            <select
              v-model="createForm.patient"
              class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
            >
              <option value="" disabled>Choose a patient</option>
              <option v-for="p in allPatients" :key="p.name" :value="p.name">
                {{ p.full_name || p.name }} ({{ p.phone || p.name }})
              </option>
            </select>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-xs font-bold text-slate-700 mb-1">Appointment Date *</label>
              <input
                v-model="createForm.appointment_date"
                type="date"
                class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
              />
            </div>
            <div>
              <label class="block text-xs font-bold text-slate-700 mb-1">Appointment Time *</label>
              <input
                v-model="createForm.appointment_time"
                type="time"
                class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
              />
            </div>
          </div>

          <div>
            <label class="block text-xs font-bold text-slate-700 mb-1">Reason for Visit</label>
            <input
              v-model="createForm.reason"
              type="text"
              placeholder="e.g. Follow-up, Routine consultation"
              class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
            />
          </div>

          <div>
            <label class="block text-xs font-bold text-slate-700 mb-1">Initial Symptoms / Notes</label>
            <textarea
              v-model="createForm.symptoms"
              rows="2"
              placeholder="Symptoms or clinical notes"
              class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
            ></textarea>
          </div>
        </div>

        <div class="modal-footer gap-2">
          <Button label="Cancel" variant="subtle" @click="showCreateModal = false" />
          <Button
            label="Book Appointment"
            theme="green"
            variant="solid"
            :loading="creatingAppt"
            @click="handleCreateAppointment"
          />
        </div>
      </div>
    </div>

    <!-- Edit Appointment Modal -->
    <div v-if="showEditModal" class="modal-backdrop" @click.self="showEditModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <div>
            <h3>Edit Appointment</h3>
            <p class="text-xs text-slate-500">Patient: {{ editForm.patient_name }} ({{ editForm.name }})</p>
          </div>
          <button class="close-btn" @click="showEditModal = false">✕</button>
        </div>

        <div class="modal-body space-y-4">
          <div v-if="editError" class="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl">
            {{ editError }}
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-xs font-bold text-slate-700 mb-1">Date</label>
              <input
                v-model="editForm.appointment_date"
                type="date"
                class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
              />
            </div>
            <div>
              <label class="block text-xs font-bold text-slate-700 mb-1">Time</label>
              <input
                v-model="editForm.appointment_time"
                type="time"
                class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
              />
            </div>
          </div>

          <div>
            <label class="block text-xs font-bold text-slate-700 mb-1">Reason for Visit</label>
            <input
              v-model="editForm.reason"
              type="text"
              class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
            />
          </div>

          <div>
            <label class="block text-xs font-bold text-slate-700 mb-1">Symptoms / Notes</label>
            <textarea
              v-model="editForm.symptoms"
              rows="2"
              class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
            ></textarea>
          </div>
        </div>

        <div class="modal-footer gap-2">
          <Button label="Cancel" variant="subtle" @click="showEditModal = false" />
          <Button
            label="Save Changes"
            theme="green"
            variant="solid"
            :loading="editingAppt"
            @click="handleEditAppointment"
          />
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div v-if="showDeleteModal" class="modal-backdrop" @click.self="showDeleteModal = false">
      <div class="modal-card max-w-sm">
        <div class="modal-header">
          <div>
            <h3 class="text-red-600">Delete Appointment?</h3>
            <p class="text-xs text-slate-500">Record: {{ selectedForDelete?.name }}</p>
          </div>
          <button class="close-btn" @click="showDeleteModal = false">✕</button>
        </div>

        <div class="modal-body">
          <div v-if="deleteError" class="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl mb-3">
            {{ deleteError }}
          </div>
          <p class="text-sm text-slate-700">
            Are you sure you want to permanently delete appointment <strong>{{ selectedForDelete?.name }}</strong> with <strong>{{ selectedForDelete?.patient_name || selectedForDelete?.patient }}</strong> on {{ formatDate(selectedForDelete?.appointment_date) }}?
          </p>
          <p class="text-xs text-slate-500 mt-2">
            This will release the booked slot and remove this appointment from your schedule.
          </p>
        </div>

        <div class="modal-footer gap-2">
          <Button label="Cancel" variant="subtle" @click="showDeleteModal = false" />
          <Button
            label="Delete Permanently"
            theme="red"
            variant="solid"
            :loading="deletingAppt"
            @click="handleDeleteAppointment"
          />
        </div>
      </div>
    </div>

  </main>
</template>

<style scoped>
.doctor-appointments-page {
  min-height: 100vh;
  padding: 32px 32px 64px;
  background:
    radial-gradient(circle at 10% 8%, rgba(13, 148, 136, 0.08), transparent 32%),
    radial-gradient(circle at 90% 12%, rgba(37, 99, 235, 0.06), transparent 30%),
    #f4f7fb;
  color: #0f172a;
}

.appointments-shell {
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

.header-copy h1 span {
  color: #0d9488;
}

.header-copy p {
  font-size: 15px;
  color: #64748b;
  margin: 0;
  max-width: 600px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

/* Controls */
.controls-row {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 28px;
}

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

.search-icon {
  margin-left: 14px;
  font-size: 16px;
  color: #94a3b8;
}

.search-input {
  flex: 1;
  padding: 12px 14px;
  border: none;
  background: transparent;
  font-size: 14px;
  outline: none;
  color: #0f172a;
}

.clear-btn {
  padding: 6px 12px;
  background: none;
  border: none;
  color: #94a3b8;
  cursor: pointer;
}

.filter-tabs {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: white;
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.tab-btn:hover {
  background: #f8fafc;
  color: #0f172a;
}

.tab-btn.active {
  background: #0d9488;
  color: white;
  border-color: #0d9488;
  box-shadow: 0 4px 12px rgba(13, 148, 136, 0.25);
}

.tab-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #475569;
}

.tab-btn.active .tab-badge {
  background: rgba(255, 255, 255, 0.25);
  color: white;
}

/* Appointment Grid */
.appointment-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 20px;
}

.appointment-card {
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

.appointment-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 36px rgba(15, 23, 42, 0.08);
  border-color: rgba(13, 148, 136, 0.4);
}

.card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.patient-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.patient-avatar {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: linear-gradient(135deg, #0d9488 0%, #2563eb 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 800;
  box-shadow: 0 4px 12px rgba(13, 148, 136, 0.2);
  flex-shrink: 0;
}

.patient-name {
  font-size: 15px;
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

/* Status Tag */
.status-tag {
  font-size: 11px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 999px;
  text-transform: capitalize;
  letter-spacing: 0.3px;
}

.status-pending   { background: #fef3c7; color: #b45309; }
.status-confirmed { background: #d1fae5; color: #047857; }
.status-completed { background: #dbeafe; color: #1e40af; }
.status-cancelled { background: #fee2e2; color: #b91c1c; }

/* Schedule Strip */
.schedule-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f8fafc;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 12px;
}

.strip-item {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #475569;
}

.strip-item strong {
  color: #0f172a;
}

.strip-item.fee {
  font-weight: 700;
  color: #0d9488;
}

/* Reason box */
.reason-box {
  font-size: 12px;
  background: #f1f5f9;
  padding: 10px 12px;
  border-radius: 10px;
  line-height: 1.4;
}

.reason-label {
  font-weight: 700;
  color: #475569;
  margin-right: 4px;
}

.reason-text {
  color: #1e293b;
}

/* Clinical Box */
.clinical-box {
  font-size: 12px;
  background: #eff6ff;
  border: 1px solid #dbeafe;
  padding: 10px 12px;
  border-radius: 10px;
  color: #1e40af;
  line-height: 1.4;
}

/* Card Actions */
.card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid #f1f5f9;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 700;
  background: #0d9488;
  color: white;
  border: none;
  cursor: pointer;
  flex: 1;
  transition: all 0.15s;
}

.btn-primary:hover {
  background: #0f766e;
  box-shadow: 0 4px 12px rgba(13, 148, 136, 0.25);
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 8px 12px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 700;
  background: white;
  border: 1px solid #e2e8f0;
  color: #475569;
  cursor: pointer;
}

.btn-secondary:hover {
  background: #f8fafc;
  color: #0f172a;
}

.btn-danger-outline {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 8px 12px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 700;
  background: #fff5f5;
  border: 1px solid #fed7d7;
  color: #c53030;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-danger-outline:hover {
  background: #fed7d7;
  color: #9b2c2c;
}

.btn-status-confirm {
  padding: 8px 12px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 700;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  color: #047857;
  cursor: pointer;
}

.btn-status-confirm:hover { background: #d1fae5; }

.btn-status-complete {
  padding: 8px 12px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 700;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  color: #1e40af;
  cursor: pointer;
}

.btn-status-complete:hover { background: #dbeafe; }

.btn-status-cancel {
  padding: 8px 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 700;
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
  cursor: pointer;
}

.btn-status-cancel:hover { background: #fee2e2; }

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

.reset-btn {
  margin-top: 12px;
  padding: 8px 16px;
  background: #0d9488;
  color: white;
  border: none;
  border-radius: 10px;
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
}

.card-skeleton {
  height: 200px;
  background: white;
  border-radius: 20px;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
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
  max-width: 520px;
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

.modal-header h3 {
  font-size: 16px;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 16px;
  color: #94a3b8;
  cursor: pointer;
}

.modal-body {
  padding: 20px 24px;
  overflow-y: auto;
  flex: 1;
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid #f1f5f9;
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 640px) {
  .doctor-appointments-page { padding: 20px 16px; }
  .page-header { flex-direction: column; align-items: flex-start; }
  .appointment-grid { grid-template-columns: 1fr; }
}
</style>
