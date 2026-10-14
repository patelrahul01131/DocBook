<script setup>
import { ref, onMounted, computed } from 'vue'
import { call, uploadFile } from '../../api'

const doctors = ref([])
const selectedDoctor = ref('')
const queueData = ref({ now_serving: null, queue: [], other: [], waiting_count: 0 })
const loading = ref(true)
const error = ref(null)
const busy = ref(false)

// Queue date — defaults to today, receptionist can move day to day.
const todayStr = new Date().toISOString().slice(0, 10)
const selectedDate = ref(todayStr)
const isToday = computed(() => selectedDate.value === todayStr)

// External report upload (front desk)
const showUpload = ref(false)
const uploading = ref(false)
const uploadError = ref(null)
const form = ref({ appointment: '', report_type: 'Lab', title: '', laboratory: '', findings: '', file: null })
const uploadAppointments = ref([])

// Walk-in booking (patient arrives with no appointment)
const showWalkin = ref(false)
const walkinBusy = ref(false)
const walkinError = ref(null)
const walkinSuccess = ref(null)
const walkinForm = ref({
  doctor: '', date: todayStr, time: '',
  full_name: '', email: '', phone: '', age: '', gender: 'Male',
  reason: '', symptoms: '',
})
const walkinSlots = ref([])
const slotsLoading = ref(false)
const lookupState = ref(null)

// Reschedule (early / late / different-day arrivals)
const showResched = ref(false)
const reschedBusy = ref(false)
const reschedError = ref(null)
const reschedTarget = ref(null)
const reschedForm = ref({ date: todayStr, time: '', reason: '' })
const reschedSlots = ref([])
const reschedSlotsLoading = ref(false)

function today() {
  return new Date().toISOString().slice(0, 10)
}

async function loadDoctors() {
  try {
    const res = await call('docbook.api.queue.get_queue')
    const rows = [...(res.queue || []), ...(res.other || [])]
    const seen = new Map()
    for (const r of rows) {
      if (r.doctor && !seen.has(r.doctor)) seen.set(r.doctor, r.doctor_name || r.doctor)
    }
    doctors.value = [...seen.entries()].map(([value, label]) => ({ value, label }))
    if (!selectedDoctor.value && doctors.value.length) {
      selectedDoctor.value = doctors.value[0].value
    }
    if (!walkinForm.value.doctor && selectedDoctor.value) {
      walkinForm.value.doctor = selectedDoctor.value
    }
  } catch (e) {
    error.value = e.message || 'Unable to load doctors.'
  }
}

async function loadQueue() {
  if (!selectedDoctor.value) {
    queueData.value = { now_serving: null, queue: [], other: [], waiting_count: 0 }
    loading.value = false
    return
  }
  loading.value = true
  error.value = null
  try {
    const res = await call('docbook.api.queue.get_queue', { doctor: selectedDoctor.value, date: selectedDate.value })
    queueData.value = {
      now_serving: res.now_serving || null,
      queue: res.queue || [],
      other: res.other || [],
      waiting_count: res.waiting_count || 0,
      date: res.date,
    }
  } catch (e) {
    error.value = e.message || 'Unable to load the queue.'
  } finally {
    loading.value = false
  }
}

async function onDoctorChange() {
  await loadQueue()
}

function shiftDay(delta) {
  const d = new Date(selectedDate.value + 'T12:00:00')
  d.setDate(d.getDate() + delta)
  selectedDate.value = d.toISOString().slice(0, 10)
  loadQueue()
}

function goToday() {
  selectedDate.value = today()
  loadQueue()
}

async function checkIn(appt) {
  busy.value = true
  try {
    await call('docbook.api.queue.check_in_patient', { appointment: appt.name })
    await loadQueue()
  } catch (e) {
    error.value = e.message || 'Check-in failed.'
  } finally {
    busy.value = false
  }
}

async function callNext() {
  busy.value = true
  error.value = null
  try {
    await call('docbook.api.queue.call_next_patient', { doctor: selectedDoctor.value, date: selectedDate.value })
    await loadQueue()
  } catch (e) {
    error.value = e.message || 'Unable to call next patient.'
  } finally {
    busy.value = false
  }
}

async function completeVisit(appt) {
  busy.value = true
  try {
    await call('docbook.api.queue.mark_visit_completed', { appointment: appt.name })
    await loadQueue()
  } catch (e) {
    error.value = e.message || 'Unable to complete visit.'
  } finally {
    busy.value = false
  }
}

// --- Walk-in booking ---
function openWalkin(presetDoctor) {
  walkinError.value = null
  walkinSuccess.value = null
  lookupState.value = null
  walkinSlots.value = []
  walkinForm.value = {
    doctor: presetDoctor || selectedDoctor.value || '',
    date: selectedDate.value || today(),
    time: '',
    full_name: '', email: '', phone: '', age: '', gender: 'Male',
    reason: '', symptoms: '',
  }
  showWalkin.value = true
  loadWalkinSlots()
}

async function lookupWalkinPatient() {
  walkinError.value = null
  lookupState.value = null
  const { email, phone } = walkinForm.value
  if (!email?.trim() && !phone?.trim()) {
    walkinError.value = 'Enter an email or phone number to look up a returning patient.'
    return
  }
  busy.value = true
  try {
    const res = await call('docbook.api.queue.lookup_patient', {
      email: email?.trim() || undefined,
      phone: phone?.trim() || undefined,
    })
    if (res.found) {
      lookupState.value = res
      walkinForm.value.full_name = walkinForm.value.full_name || res.full_name || ''
      if (res.age) walkinForm.value.age = res.age
      if (res.gender) walkinForm.value.gender = res.gender
    } else {
      lookupState.value = { found: false }
    }
  } catch (e) {
    walkinError.value = e.message || 'Lookup failed.'
  } finally {
    busy.value = false
  }
}

async function loadWalkinSlots() {
  walkinSlots.value = []
  const { doctor, date } = walkinForm.value
  if (!doctor || !date) return
  slotsLoading.value = true
  try {
    const res = await call('docbook.api.appointment.get_available_slots', { doctor, date })
    walkinSlots.value = Array.isArray(res) ? res : (res.slots || [])
  } catch (e) {
    walkinSlots.value = []
  } finally {
    slotsLoading.value = false
  }
}

async function submitWalkin() {
  walkinError.value = null
  walkinSuccess.value = null
  const f = walkinForm.value
  if (!f.doctor) { walkinError.value = 'Please choose a doctor.'; return }
  if (!f.full_name?.trim() || !f.email?.trim()) {
    walkinError.value = 'Patient name and email are required (a login is auto-created for new patients).'
    return
  }
  if (!f.date) { walkinError.value = 'Please choose a date.'; return }
  if (f.date !== today() && !f.time) {
    walkinError.value = 'Please pick a time slot for a future-date walk-in.'
    return
  }
  walkinBusy.value = true
  try {
    const res = await call('docbook.api.queue.create_walkin_appointment', {
      doctor: f.doctor,
      appointment_date: f.date,
      appointment_time: f.time || undefined,
      full_name: f.full_name.trim(),
      email: f.email.trim(),
      phone: f.phone?.trim() || undefined,
      age: f.age || undefined,
      gender: f.gender || undefined,
      reason: f.reason?.trim() || undefined,
      symptoms: f.symptoms?.trim() || undefined,
    })
    walkinSuccess.value = `Token #${res.token} — ${res.appointment_date} ${res.appointment_time}`
    if (res.user_created) walkinSuccess.value += ' · new patient login created'
    await loadDoctors()
    await loadQueue()
  } catch (e) {
    walkinError.value = e.message || 'Walk-in booking failed.'
  } finally {
    walkinBusy.value = false
  }
}

// --- Front-desk external report upload ---
function openUpload(appt) {
  uploadError.value = null
  form.value = { appointment: appt ? appt.name : '', report_type: 'Lab', title: '', laboratory: '', findings: '', file: null }
  uploadAppointments.value = appt ? [appt] : []
  showUpload.value = true
}

function onFileChange(e) {
  form.value.file = e.target.files?.[0] || null
}

async function submitUpload() {
  uploadError.value = null
  const f = form.value
  if (!f.appointment || !f.title?.trim()) {
    uploadError.value = 'Appointment and title are required.'
    return
  }
  uploading.value = true
  try {
    let fileUrl = ''
    if (f.file) fileUrl = (await uploadFile(f.file)) || ''
    await call('docbook.api.report.upload_external_report', {
      appointment: f.appointment,
      file_url: fileUrl,
      report_type: f.report_type,
      title: f.title,
      findings: f.findings || '',
      laboratory: f.laboratory || '',
    })
    showUpload.value = false
    await loadQueue()
  } catch (e) {
    uploadError.value = e.message || 'Upload failed.'
  } finally {
    uploading.value = false
  }
}

// --- Reschedule (early / late / different-day arrivals) ---
function openReschedule(appt) {
  reschedError.value = null
  reschedTarget.value = appt
  reschedSlots.value = []
  reschedForm.value = { date: appt.appointment_date || today(), time: '', reason: '' }
  showResched.value = true
  loadReschedSlots()
}

async function loadReschedSlots() {
  reschedSlots.value = []
  if (!reschedTarget.value || !reschedForm.value.date) return
  reschedSlotsLoading.value = true
  try {
    const res = await call('docbook.api.appointment.get_available_slots', {
      doctor: reschedTarget.value.doctor,
      date: reschedForm.value.date,
      exclude_appointment: reschedTarget.value.name,
    })
    reschedSlots.value = Array.isArray(res) ? res : (res.slots || [])
  } catch (e) {
    reschedSlots.value = []
  } finally {
    reschedSlotsLoading.value = false
  }
}

async function submitReschedule() {
  reschedError.value = null
  if (!reschedForm.value.date || !reschedForm.value.time) {
    reschedError.value = 'Please pick a new date and time slot.'
    return
  }
  reschedBusy.value = true
  try {
    await call('docbook.api.queue.receptionist_reschedule', {
      appointment: reschedTarget.value.name,
      appointment_date: reschedForm.value.date,
      appointment_time: reschedForm.value.time,
      reason: reschedForm.value.reason?.trim() || undefined,
    })
    showResched.value = false
    await loadQueue()
  } catch (e) {
    reschedError.value = e.message || 'Reschedule failed.'
  } finally {
    reschedBusy.value = false
  }
}

function stageClass(stage) {
  const s = (stage || '').toLowerCase().replace(/\s+/g, '-')
  return `q-stage q-stage--${s}`
}

const waitingList = computed(() => queueData.value.queue || [])
const notCheckedIn = computed(() =>
  (queueData.value.other || []).filter((a) => !a.checked_in && a.status !== 'Cancelled')
)

onMounted(async () => {
  await loadDoctors()
  await loadQueue()
})
</script>

<template>
  <div class="db-page">
    <div class="db-container">
      <header class="q-header">
        <div>
          <div class="db-eyebrow">RECEPTIONIST PORTAL</div>
          <h1 class="db-page-title">Queue Management</h1>
          <p class="db-section-subtitle">Check patients in, call the next, book walk-ins, and reschedule early/late arrivals.</p>
          <p class="db-section-subtitle">Showing {{ isToday ? 'today' : selectedDate }} · {{ queueData.waiting_count }} waiting</p>
        </div>
        <div class="q-head-actions">
          <div class="q-date-nav">
            <button class="db-btn" @click="shiftDay(-1)" title="Previous day">‹</button>
            <input type="date" v-model="selectedDate" class="q-select q-date" @change="loadQueue" />
            <button class="db-btn" @click="shiftDay(1)" title="Next day">›</button>
            <button v-if="!isToday" class="db-btn" @click="goToday">Today</button>
          </div>
          <select v-model="selectedDoctor" class="q-select" @change="onDoctorChange">
            <option value="" disabled>Select doctor</option>
            <option v-for="d in doctors" :key="d.value" :value="d.value">{{ d.label }}</option>
          </select>
          <button class="db-btn db-btn--secondary" :disabled="!selectedDoctor" @click="openWalkin(selectedDoctor)">+ Walk-in</button>
          <button class="db-btn db-btn--primary" :disabled="busy || !selectedDoctor || !isToday" @click="callNext" title="Call next works on today's live queue">🔔 Call Next</button>
        </div>
      </header>

      <div v-if="error" class="db-error-panel">
        <span>⚠️</span><span>{{ error }}</span>
        <button class="db-btn db-btn--secondary" style="margin-left:auto" @click="loadQueue">Retry</button>
      </div>

      <!-- Now serving -->
      <div v-if="queueData.now_serving" class="q-now">
        <div class="q-now-label">NOW SERVING</div>
        <div class="q-now-body">
          <span class="q-token">#{{ queueData.now_serving.queue_token || '—' }}</span>
          <span class="q-now-name">{{ queueData.now_serving.patient_name || queueData.now_serving.patient }}</span>
          <span :class="stageClass(queueData.now_serving.visit_stage)">{{ queueData.now_serving.visit_stage }}</span>
        </div>
      </div>

      <div v-if="loading" class="q-grid">
        <div v-for="i in 3" :key="i" class="db-card" style="min-height:90px"></div>
      </div>

      <div v-else>
        <!-- Active queue -->
        <section class="q-section">
          <h2 class="q-section-title">In queue · {{ waitingList.length }}</h2>
          <div v-if="waitingList.length === 0" class="db-empty">
            <div class="db-empty-icon">🪑</div><h3>Queue is empty</h3>
            <p>Checked-in patients will appear here in call order.</p>
          </div>
          <div v-else class="q-list">
            <div v-for="a in waitingList" :key="a.name" class="db-card q-row" :class="{ 'q-row--priority': a.priority }">
              <span class="q-pos">{{ a.queue_position }}</span>
              <span class="q-token">#{{ a.queue_token || '—' }}</span>
              <div class="q-info">
                <p class="q-name">{{ a.patient_name || a.patient }}</p>
                <p class="q-sub">{{ a.appointment_time }} · {{ a.name }}</p>
              </div>
              <span :class="stageClass(a.visit_stage)">{{ a.visit_stage }}</span>
              <span v-if="a.priority" class="q-flag">Return · skip queue</span>
              <div class="q-actions">
                <button class="db-btn db-btn--secondary" @click="openUpload(a)">⬆ Report</button>
                <button class="db-btn db-btn--secondary" @click="openReschedule(a)">Reschedule</button>
                <button class="db-btn db-btn--ghost" @click="completeVisit(a)">✓ Done</button>
              </div>
            </div>
          </div>
        </section>

        <!-- Not checked in -->
        <section class="q-section">
          <h2 class="q-section-title">Awaiting check-in · {{ notCheckedIn.length }}</h2>
          <div v-if="notCheckedIn.length === 0" class="db-empty">
            <div class="db-empty-icon">✅</div><h3>Everyone is checked in</h3>
          </div>
          <div v-else class="q-list">
            <div v-for="a in notCheckedIn" :key="a.name" class="db-card q-row">
              <div class="q-info">
                <p class="q-name">{{ a.patient_name || a.patient }}</p>
                <p class="q-sub">{{ a.appointment_time }} · {{ a.name }} · {{ a.doctor_name || a.doctor }}</p>
              </div>
              <span :class="stageClass(a.visit_stage || 'Scheduled')">{{ a.visit_stage || 'Scheduled' }}</span>
              <div class="q-actions">
                <button class="db-btn db-btn--secondary" @click="openUpload(a)">⬆ Report</button>
                <button class="db-btn db-btn--secondary" @click="openReschedule(a)">Reschedule</button>
                <button class="db-btn db-btn--primary" :disabled="busy" @click="checkIn(a)">Check In</button>
              </div>
            </div>
          </div>
        </section>
      </div>

      <!-- Upload modal -->
      <div v-if="showUpload" class="q-overlay" @click.self="showUpload = false">
        <div class="q-modal">
          <div class="q-modal-head">
            <h3>Register report (front desk)</h3>
            <button class="q-close" @click="showUpload = false">✕</button>
          </div>
          <div class="q-modal-body">
            <div v-if="uploadError" class="q-error">{{ uploadError }}</div>
            <label class="q-label">Report type</label>
            <select v-model="form.report_type" class="q-input">
              <option>Lab</option><option>Imaging</option><option>Prescription</option>
              <option>Document</option><option>Other</option>
            </select>
            <label class="q-label">Title</label>
            <input v-model="form.title" class="q-input" placeholder="e.g. X-Ray Chest" />
            <label class="q-label">Laboratory / Provider</label>
            <input v-model="form.laboratory" class="q-input" placeholder="e.g. Thyrocare" />
            <label class="q-label">File</label>
            <input type="file" class="q-input" @change="onFileChange" />
            <label class="q-label">Findings (optional)</label>
            <textarea v-model="form.findings" class="q-input" rows="3"></textarea>
          </div>
          <div class="q-modal-foot">
            <button class="db-btn db-btn--secondary" @click="showUpload = false">Cancel</button>
            <button class="db-btn db-btn--primary" :disabled="uploading" @click="submitUpload">
              {{ uploading ? 'Uploading…' : 'Upload' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Walk-in modal -->
      <div v-if="showWalkin" class="q-overlay" @click.self="showWalkin = false">
        <div class="q-modal q-modal--wide">
          <div class="q-modal-head">
            <h3>Walk-in booking</h3>
            <button class="q-close" @click="showWalkin = false">✕</button>
          </div>
          <div class="q-modal-body">
            <div v-if="walkinError" class="q-error">{{ walkinError }}</div>
            <div v-if="walkinSuccess" class="q-success">{{ walkinSuccess }}</div>
            <label class="q-label">Email (for lookup / new login)</label>
            <div class="q-inline">
              <input v-model="walkinForm.email" class="q-input" placeholder="patient@example.com" />
              <button class="db-btn db-btn--secondary" :disabled="busy" @click="lookupWalkinPatient">Find</button>
            </div>
            <label class="q-label">Phone</label>
            <div class="q-inline">
              <input v-model="walkinForm.phone" class="q-input" placeholder="+91…" />
              <button class="db-btn db-btn--secondary" :disabled="busy" @click="lookupWalkinPatient">Find</button>
            </div>
            <div v-if="lookupState" class="q-lookup">
              <span v-if="lookupState.found">✓ Returning patient: <strong>{{ lookupState.full_name }}</strong></span>
              <span v-else class="q-lookup-new">New patient — a login will be auto-created.</span>
            </div>
            <label class="q-label">Full name *</label>
            <input v-model="walkinForm.full_name" class="q-input" placeholder="Patient name" />
            <div class="q-grid-2">
              <div>
                <label class="q-label">Age</label>
                <input v-model="walkinForm.age" type="number" min="0" max="150" class="q-input" />
              </div>
              <div>
                <label class="q-label">Gender</label>
                <select v-model="walkinForm.gender" class="q-input">
                  <option>Male</option><option>Female</option><option>Other</option>
                </select>
              </div>
            </div>
            <div class="q-grid-2">
              <div>
                <label class="q-label">Doctor *</label>
                <select v-model="walkinForm.doctor" class="q-input" @change="loadWalkinSlots">
                  <option value="" disabled>Select doctor</option>
                  <option v-for="d in doctors" :key="d.value" :value="d.value">{{ d.label }}</option>
                </select>
              </div>
              <div>
                <label class="q-label">Date *</label>
                <input type="date" v-model="walkinForm.date" class="q-input" :min="todayStr" @change="loadWalkinSlots" />
              </div>
            </div>
            <label class="q-label">Time slot {{ walkinForm.date === todayStr ? '(optional — now if blank)' : '*' }}</label>
            <select v-model="walkinForm.time" class="q-input">
              <option value="">{{ walkinForm.date === todayStr ? 'Now (patient is here)' : 'Select a slot' }}</option>
              <option v-for="s in walkinSlots" :key="s.start_time" :value="s.start_time">{{ s.formatted }}</option>
            </select>
            <p v-if="slotsLoading" class="q-sub">Loading slots…</p>
            <p v-else-if="walkinForm.doctor && walkinForm.date && !walkinSlots.length" class="q-sub">No free slots for this doctor/date.</p>
            <label class="q-label">Reason</label>
            <input v-model="walkinForm.reason" class="q-input" placeholder="e.g. Fever" />
            <label class="q-label">Symptoms</label>
            <input v-model="walkinForm.symptoms" class="q-input" placeholder="e.g. Cough, cold" />
          </div>
          <div class="q-modal-foot">
            <button class="db-btn db-btn--secondary" @click="showWalkin = false">Close</button>
            <button class="db-btn db-btn--primary" :disabled="walkinBusy" @click="submitWalkin">
              {{ walkinBusy ? 'Booking…' : 'Book & check in' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Reschedule modal -->
      <div v-if="showResched" class="q-overlay" @click.self="showResched = false">
        <div class="q-modal">
          <div class="q-modal-head">
            <h3>Reschedule {{ reschedTarget?.name }}</h3>
            <button class="q-close" @click="showResched = false">✕</button>
          </div>
          <div class="q-modal-body">
            <div v-if="reschedError" class="q-error">{{ reschedError }}</div>
            <p class="q-sub">Currently {{ reschedTarget?.appointment_date }} {{ reschedTarget?.appointment_time }}. Same-day keeps check-in; a new day resets the queue.</p>
            <label class="q-label">New date *</label>
            <input type="date" v-model="reschedForm.date" class="q-input" :min="todayStr" @change="loadReschedSlots" />
            <label class="q-label">New time slot *</label>
            <select v-model="reschedForm.time" class="q-input">
              <option value="">Select a slot</option>
              <option v-for="s in reschedSlots" :key="s.start_time" :value="s.start_time">{{ s.formatted }}</option>
            </select>
            <p v-if="reschedSlotsLoading" class="q-sub">Loading slots…</p>
            <p v-else-if="reschedForm.date && !reschedSlots.length" class="q-sub">No free slots on this date.</p>
            <label class="q-label">Reason (optional)</label>
            <input v-model="reschedForm.reason" class="q-input" placeholder="e.g. Came a day early" />
          </div>
          <div class="q-modal-foot">
            <button class="db-btn db-btn--secondary" @click="showResched = false">Cancel</button>
            <button class="db-btn db-btn--primary" :disabled="reschedBusy" @click="submitReschedule">
              {{ reschedBusy ? 'Moving…' : 'Reschedule' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.q-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }
.q-head-actions { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.q-select { padding: 9px 12px; border: 1px solid #e2e8f0; border-radius: 10px; font-size: 13px; font-weight: 600; color: #0f172a; background: #fff; outline: none; min-width: 180px; }

.q-now { background: linear-gradient(120deg, #0d9488, #0e7490); color: #fff; border-radius: 16px; padding: 18px 22px; margin-bottom: 24px; box-shadow: 0 8px 24px rgba(13,148,136,0.25); }
.q-now-label { font-size: 10px; font-weight: 800; letter-spacing: 1.4px; opacity: 0.85; }
.q-now-body { display: flex; align-items: center; gap: 14px; margin-top: 6px; flex-wrap: wrap; }
.q-token { font-size: 22px; font-weight: 900; font-variant-numeric: tabular-nums; }
.q-now-name { font-size: 18px; font-weight: 800; }

.q-section { margin-bottom: 28px; }
.q-section-title { font-size: 13px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.8px; color: #64748b; margin: 0 0 12px; }
.q-list { display: flex; flex-direction: column; gap: 10px; }

.q-row { display: flex; align-items: center; gap: 14px; padding: 14px 16px; }
.q-row--priority { border-left: 4px solid #f59e0b; background: #fffbeb; }
.q-pos { width: 30px; height: 30px; border-radius: 50%; background: #f1f5f9; color: #0f172a; font-weight: 800; font-size: 13px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.q-row .q-token { font-size: 15px; color: #0d9488; width: 48px; flex-shrink: 0; }
.q-info { flex: 1; min-width: 0; }
.q-name { margin: 0; font-size: 14px; font-weight: 700; color: #0f172a; }
.q-sub { margin: 2px 0 0; font-size: 12px; color: #64748b; }
.q-flag { font-size: 11px; font-weight: 700; color: #b45309; background: #fef3c7; padding: 3px 8px; border-radius: 999px; }
.q-actions { display: flex; gap: 8px; flex-shrink: 0; }

.q-stage { font-size: 11px; font-weight: 700; padding: 4px 9px; border-radius: 999px; background: #f1f5f9; color: #475569; white-space: nowrap; }
.q-stage--waiting { background: #fef3c7; color: #92400e; }
.q-stage--in-consultation { background: #d1fae5; color: #065f46; }
.q-stage--ready-for-review { background: #dbeafe; color: #1e40af; }
.q-stage--report-pending { background: #ede9fe; color: #5b21b6; }
.q-stage--completed { background: #d1fae5; color: #065f46; }
.q-stage--scheduled { background: #f1f5f9; color: #64748b; }

.q-overlay { position: fixed; inset: 0; background: rgba(15,23,42,0.4); backdrop-filter: blur(3px); z-index: 1000; display: flex; align-items: center; justify-content: center; padding: 20px; }
.q-modal { background: #fff; border-radius: 16px; width: 100%; max-width: 440px; max-height: 88vh; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 24px 64px rgba(15,23,42,0.2); }
.q-modal-head { display: flex; justify-content: space-between; align-items: center; padding: 18px 20px; border-bottom: 1px solid #f1f5f9; }
.q-modal-head h3 { margin: 0; font-size: 16px; font-weight: 800; color: #0f172a; }
.q-close { background: none; border: none; font-size: 16px; color: #94a3b8; cursor: pointer; }
.q-modal-body { padding: 18px 20px; overflow-y: auto; }
.q-modal-foot { display: flex; justify-content: flex-end; gap: 10px; padding: 14px 20px; border-top: 1px solid #f1f5f9; }
.q-label { display: block; font-size: 12px; font-weight: 700; color: #475569; margin: 12px 0 6px; }
.q-input { width: 100%; padding: 9px 11px; border: 1px solid #e2e8f0; border-radius: 9px; font-size: 13px; color: #0f172a; outline: none; font-family: inherit; box-sizing: border-box; }
.q-input:focus { border-color: #0d9488; box-shadow: 0 0 0 3px rgba(13,148,136,0.12); }
.q-error { background: #fef2f2; border: 1px solid #fecaca; color: #b91c1c; font-size: 12px; padding: 10px 12px; border-radius: 9px; margin-bottom: 8px; }
.q-success { background: #ecfdf5; border: 1px solid #a7f3d0; color: #065f46; font-size: 12px; padding: 10px 12px; border-radius: 9px; margin-bottom: 8px; }
.q-modal--wide { max-width: 560px; }
.q-inline { display: flex; gap: 8px; }
.q-inline .q-input { flex: 1; }
.q-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 0 12px; }
.q-lookup { font-size: 12px; color: #0f766e; background: #f0fdfa; border: 1px solid #99f6e4; border-radius: 9px; padding: 8px 12px; margin-top: 8px; }
.q-lookup-new { color: #92400e; }
.q-date-nav { display: flex; align-items: center; gap: 6px; }
.q-date { min-width: 150px; }

@media (max-width: 720px) {
  .q-header { flex-direction: column; }
  .q-row { flex-wrap: wrap; }
  .q-actions { width: 100%; justify-content: flex-end; }
}
</style>


