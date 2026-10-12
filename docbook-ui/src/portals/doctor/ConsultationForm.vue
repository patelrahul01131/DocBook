<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { call } from '../../api'

const route = useRoute()
const router = useRouter()

const appointmentId = route.params.id
const appointment = ref(null)
const loading = ref(false)
const error = ref(null)

// Consultation form
const consultation = reactive({
  symptoms: '',
  diagnosis: '',
  consultation_notes: '',
  treatment_plan: '',
  follow_up_date: '',
  follow_up_instructions: '',
})
const savingConsultation = ref(false)
const consultationSaved = ref(false)
const consultationError = ref(null)

// Prescription form
const prescription = ref(null)
const creatingPrescription = ref(false)
const prescriptionError = ref(null)

// Edit prescription modal
const showEditPrxModal = ref(false)
const editingPrx = ref(false)
const editPrxError = ref(null)
const editPrxForm = reactive({
  diagnosis: '',
  instructions: '',
  follow_up_date: '',
  notes: '',
  status: 'Active',
})

// Delete prescription modal
const showDeletePrxModal = ref(false)
const deletingPrx = ref(false)
const deletePrxError = ref(null)

// Add medicine form
const medicineSearch = ref('')
const medicineResults = ref([])
const searchLoading = ref(false)
const showMedicineForm = ref(false)
const selectedMedicine = ref(null)

const medForm = reactive({
  medicine: '',
  medicine_name: '',
  dosage: '',
  route: 'Oral',
  frequency: 'Once Daily',
  start_date: '',
  end_date: '',
  dose_time_1: '',
  dose_time_2: '',
  dose_time_3: '',
  dose_time_4: '',
  instructions: '',
})
const addingMedicine = ref(false)
const addMedError = ref(null)

const prescribedMedicines = ref([])
const loadingMedicines = ref(false)

// Edit medicine modal
const showEditMedModal = ref(false)
const editingMed = ref(false)
const editMedError = ref(null)
const editMedForm = reactive({
  name: '',
  medicine_name: '',
  dosage: '',
  route: 'Oral',
  frequency: 'Once Daily',
  start_date: '',
  end_date: '',
  dose_time_1: '',
  dose_time_2: '',
  dose_time_3: '',
  dose_time_4: '',
  instructions: '',
  status: 'Active',
})

// Delete medicine modal
const showDeleteMedModal = ref(false)
const deletingMed = ref(false)
const deleteMedError = ref(null)
const selectedMedForDelete = ref(null)

// Medical history form
const historyForm = reactive({
  medical_condition: '',
  description: '',
  symptoms: '',
  allergies: '',
  record_type: 'Medical Condition',
  status: 'Active',
  severity: '',
})
const savingHistory = ref(false)
const historySaved = ref(false)
const historyError = ref(null)
const showHistoryForm = ref(false)

async function fetchAppointment() {
  loading.value = true
  error.value = null
  try {
    let found = null
    try {
      found = await call('docbook.api.appointment.show_appointment', { appointment_id: appointmentId })
    } catch (e) {
      console.warn('show_appointment failed, trying doctor appointments list', e)
    }

    if (!found) {
      const appts = await call('docbook.api.prescription.get_doctor_appointments')
      found = Array.isArray(appts) ? appts.find(a => a.name === appointmentId) : null
    }

    if (!found) throw new Error('Appointment not found or you do not have access.')
    appointment.value = found
    consultation.symptoms = found.symptoms || ''
    consultation.diagnosis = found.diagnosis || ''
    consultation.consultation_notes = found.consultation_notes || ''
    consultation.treatment_plan = found.treatment_plan || ''
    consultation.follow_up_date = found.follow_up_date || ''
    consultation.follow_up_instructions = found.follow_up_instructions || ''
    await fetchPrescription()
  } catch (e) {
    error.value = e.message || 'Unable to load appointment.'
  } finally {
    loading.value = false
  }
}

async function fetchPrescription() {
  try {
    const prescriptions = await call('docbook.api.prescription.get_doctor_prescriptions')
    const found = Array.isArray(prescriptions)
      ? prescriptions.find(p => p.appointment === appointmentId)
      : null
    prescription.value = found || null
    if (found) await fetchPrescribedMedicines(found.name)
  } catch { }
}

async function fetchPrescribedMedicines(prescriptionName) {
  loadingMedicines.value = true
  try {
    const detail = await call('docbook.api.prescription.get_prescription_detail', {
      prescription_name: prescriptionName,
    })
    prescribedMedicines.value = detail?.medicines || []
  } catch {
    prescribedMedicines.value = []
  } finally {
    loadingMedicines.value = false
  }
}

async function saveConsultation() {
  savingConsultation.value = true
  consultationError.value = null
  consultationSaved.value = false
  try {
    await call('docbook.api.prescription.record_consultation', {
      appointment: appointmentId,
      ...consultation,
    })
    consultationSaved.value = true
    setTimeout(() => { consultationSaved.value = false }, 3000)
  } catch (e) {
    consultationError.value = e.message || 'Failed to save consultation.'
  } finally {
    savingConsultation.value = false
  }
}

async function createPrescription() {
  if (!appointment.value) return
  creatingPrescription.value = true
  prescriptionError.value = null
  try {
    await call('docbook.api.prescription.create_prescription', {
      patient: appointment.value.patient,
      appointment: appointmentId,
      diagnosis: consultation.diagnosis,
      follow_up_date: consultation.follow_up_date,
    })
    await fetchPrescription()
  } catch (e) {
    prescriptionError.value = e.message || 'Failed to create prescription.'
  } finally {
    creatingPrescription.value = false
  }
}

// ---- Edit Prescription ----
function openEditPrxModal() {
  if (!prescription.value) return
  editPrxError.value = null
  editPrxForm.diagnosis = prescription.value.diagnosis || ''
  editPrxForm.instructions = prescription.value.instructions || ''
  editPrxForm.follow_up_date = prescription.value.follow_up_date || ''
  editPrxForm.notes = prescription.value.notes || ''
  editPrxForm.status = prescription.value.status || 'Active'
  showEditPrxModal.value = true
}

async function handleEditPrescription() {
  if (!prescription.value) return
  editingPrx.value = true
  editPrxError.value = null
  try {
    await call('docbook.api.prescription.update_prescription', {
      prescription: prescription.value.name,
      diagnosis: editPrxForm.diagnosis || null,
      instructions: editPrxForm.instructions || null,
      follow_up_date: editPrxForm.follow_up_date || null,
      notes: editPrxForm.notes || null,
      status: editPrxForm.status || null,
    })
    showEditPrxModal.value = false
    await fetchPrescription()
  } catch (e) {
    editPrxError.value = e.message || 'Failed to update prescription.'
  } finally {
    editingPrx.value = false
  }
}

// ---- Delete Prescription ----
function openDeletePrxModal() {
  deletePrxError.value = null
  showDeletePrxModal.value = true
}

async function handleDeletePrescription() {
  if (!prescription.value) return
  deletingPrx.value = true
  deletePrxError.value = null
  try {
    await call('docbook.api.prescription.delete_prescription', {
      prescription: prescription.value.name,
    })
    showDeletePrxModal.value = false
    prescription.value = null
    prescribedMedicines.value = []
  } catch (e) {
    deletePrxError.value = e.message || 'Failed to delete prescription.'
  } finally {
    deletingPrx.value = false
  }
}

// ---- Edit Medicine ----
function openEditMedModal(med) {
  editMedError.value = null
  editMedForm.name = med.name
  editMedForm.medicine_name = med.prescribed_medicine_name || med.medicine_name || ''
  editMedForm.dosage = med.dosage || ''
  editMedForm.route = med.route || 'Oral'
  editMedForm.frequency = med.frequency || 'Once Daily'
  editMedForm.start_date = med.start_date || ''
  editMedForm.end_date = med.end_date || ''
  editMedForm.dose_time_1 = med.dose_time_1 || ''
  editMedForm.dose_time_2 = med.dose_time_2 || ''
  editMedForm.dose_time_3 = med.dose_time_3 || ''
  editMedForm.dose_time_4 = med.dose_time_4 || ''
  editMedForm.instructions = med.instructions || ''
  editMedForm.status = med.status || 'Active'
  showEditMedModal.value = true
}

async function handleEditMedicine() {
  editingMed.value = true
  editMedError.value = null
  try {
    await call('docbook.api.prescription.update_prescription_medicine', {
      medicine_record: editMedForm.name,
      dosage: editMedForm.dosage || null,
      frequency: editMedForm.frequency || null,
      route: editMedForm.route || null,
      start_date: editMedForm.start_date || null,
      end_date: editMedForm.end_date || null,
      instructions: editMedForm.instructions || null,
      dose_time_1: editMedForm.dose_time_1 || null,
      dose_time_2: editMedForm.dose_time_2 || null,
      dose_time_3: editMedForm.dose_time_3 || null,
      dose_time_4: editMedForm.dose_time_4 || null,
      status: editMedForm.status || null,
    })
    showEditMedModal.value = false
    await fetchPrescribedMedicines(prescription.value.name)
  } catch (e) {
    editMedError.value = e.message || 'Failed to update medicine.'
  } finally {
    editingMed.value = false
  }
}

// ---- Delete Medicine ----
function openDeleteMedModal(med) {
  deleteMedError.value = null
  selectedMedForDelete.value = med
  showDeleteMedModal.value = true
}

async function handleDeleteMedicine() {
  if (!selectedMedForDelete.value) return
  deletingMed.value = true
  deleteMedError.value = null
  try {
    await call('docbook.api.prescription.delete_prescription_medicine', {
      medicine_record: selectedMedForDelete.value.name,
    })
    showDeleteMedModal.value = false
    selectedMedForDelete.value = null
    await fetchPrescribedMedicines(prescription.value.name)
  } catch (e) {
    deleteMedError.value = e.message || 'Failed to delete medicine.'
  } finally {
    deletingMed.value = false
  }
}

// ---- Medicine Search / Add ----
let searchTimer = null
async function searchMedicines() {
  if (!medicineSearch.value.trim()) {
    medicineResults.value = []
    return
  }
  clearTimeout(searchTimer)
  searchLoading.value = true
  searchTimer = setTimeout(async () => {
    try {
      const res = await call('docbook.api.medicine.search_medicines', {
        query: medicineSearch.value,
        limit: 8,
      })
      medicineResults.value = Array.isArray(res) ? res : []
    } catch {
      medicineResults.value = []
    } finally {
      searchLoading.value = false
    }
  }, 280)
}

function selectMedicine(med) {
  selectedMedicine.value = med
  medForm.medicine = med.name
  medForm.medicine_name = med.medicine_name
  medicineSearch.value = med.medicine_name
  medicineResults.value = []
  const today = new Date().toISOString().slice(0, 10)
  if (!medForm.start_date) medForm.start_date = today
  showMedicineForm.value = true
}

function freqDoseTimes(freq) {
  const map = {
    'Once Daily': 1,
    'Twice Daily': 2,
    'Three Times Daily': 3,
    'Four Times Daily': 4,
  }
  return map[freq] || 0
}

async function addMedicine() {
  if (!prescription.value) {
    addMedError.value = 'Please create a prescription first.'
    return
  }
  if (!medForm.medicine) {
    addMedError.value = 'Please select a medicine.'
    return
  }
  addingMedicine.value = true
  addMedError.value = null
  try {
    await call('docbook.api.prescription.add_prescription_medicine', {
      prescription: prescription.value.name,
      medicine: medForm.medicine,
      dosage: medForm.dosage,
      route: medForm.route,
      frequency: medForm.frequency,
      start_date: medForm.start_date,
      end_date: medForm.end_date,
      dose_time_1: medForm.dose_time_1 || null,
      dose_time_2: medForm.dose_time_2 || null,
      dose_time_3: medForm.dose_time_3 || null,
      dose_time_4: medForm.dose_time_4 || null,
      instructions: medForm.instructions || null,
    })
    Object.assign(medForm, {
      medicine: '', medicine_name: '', dosage: '', route: 'Oral',
      frequency: 'Once Daily', start_date: '', end_date: '',
      dose_time_1: '', dose_time_2: '', dose_time_3: '', dose_time_4: '',
      instructions: '',
    })
    medicineSearch.value = ''
    selectedMedicine.value = null
    showMedicineForm.value = false
    await fetchPrescribedMedicines(prescription.value.name)
  } catch (e) {
    addMedError.value = e.message || 'Failed to add medicine.'
  } finally {
    addingMedicine.value = false
  }
}

async function saveHistory() {
  if (!historyForm.medical_condition) {
    historyError.value = 'Condition name is required.'
    return
  }
  savingHistory.value = true
  historyError.value = null
  historySaved.value = false
  try {
    await call('docbook.api.medical_history.create_medical_history_record', {
      patient: appointment.value?.patient,
      record_date: new Date().toISOString().slice(0, 10),
      appointment: appointmentId,
      ...historyForm,
    })
    historySaved.value = true
    showHistoryForm.value = false
    Object.assign(historyForm, {
      medical_condition: '', description: '', symptoms: '', allergies: '',
      record_type: 'Medical Condition', status: 'Active', severity: '',
    })
    setTimeout(() => { historySaved.value = false }, 3000)
  } catch (e) {
    historyError.value = e.message || 'Failed to save history record.'
  } finally {
    savingHistory.value = false
  }
}

function formatDate(d) {
  if (!d) return '—'
  return new Date(`${d}T00:00:00`).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

function statusClass(s) {
  return `db-badge db-badge--${(s || '').toLowerCase()}`
}

onMounted(fetchAppointment)
</script>

<template>
  <div class="db-page">
    <div class="db-container">
      <!-- Back button -->
      <button class="db-btn db-btn--secondary back-btn" @click="router.back()">
        ← Back
      </button>

      <!-- Loading -->
      <div v-if="loading" style="padding: 40px 0;">
        <div class="db-skeleton" style="height:18px; width:40%; margin-bottom:12px;"></div>
        <div class="db-skeleton" style="height:13px; width:60%;"></div>
      </div>

      <div v-else-if="error" class="db-error-panel">
        <span>⚠️</span>
        <span>{{ error }}</span>
        <button class="db-btn db-btn--secondary" style="margin-left:auto;" @click="fetchAppointment">Retry</button>
      </div>

      <template v-else-if="appointment">
        <!-- Appointment header -->
        <div class="appt-header">
          <div>
            <div class="db-eyebrow">CONSULTATION</div>
            <h1 class="db-page-title" style="margin-bottom:6px;">{{ appointment.patient_name || appointment.patient }}</h1>
            <div class="appt-header-meta">
              <span>📅 {{ formatDate(appointment.appointment_date) }}</span>
              <span v-if="appointment.appointment_time"> · ⏰ {{ appointment.appointment_time }}</span>
              <span v-if="appointment.gender"> · {{ appointment.gender }}</span>
              <span v-if="appointment.age"> · {{ appointment.age }} yrs</span>
            </div>
          </div>
          <span :class="statusClass(appointment.status)">{{ appointment.status }}</span>
        </div>

        <!-- SECTION: Consultation Notes -->
        <div class="db-card consult-section">
          <div class="section-head">
            <span class="section-icon">🩺</span>
            <h2 class="db-section-title">Consultation Notes</h2>
          </div>

          <div class="form-grid-2">
            <div class="db-form-group">
              <label class="db-label">Symptoms</label>
              <textarea v-model="consultation.symptoms" class="db-textarea" placeholder="Describe patient's symptoms…" rows="3"></textarea>
            </div>
            <div class="db-form-group">
              <label class="db-label">Diagnosis</label>
              <textarea v-model="consultation.diagnosis" class="db-textarea" placeholder="Primary diagnosis…" rows="3"></textarea>
            </div>
            <div class="db-form-group">
              <label class="db-label">Consultation Notes</label>
              <textarea v-model="consultation.consultation_notes" class="db-textarea" placeholder="Detailed consultation notes…" rows="3"></textarea>
            </div>
            <div class="db-form-group">
              <label class="db-label">Treatment Plan</label>
              <textarea v-model="consultation.treatment_plan" class="db-textarea" placeholder="Recommended treatment…" rows="3"></textarea>
            </div>
            <div class="db-form-group">
              <label class="db-label">Follow-up Date</label>
              <input v-model="consultation.follow_up_date" type="date" class="db-input" />
            </div>
            <div class="db-form-group">
              <label class="db-label">Follow-up Instructions</label>
              <textarea v-model="consultation.follow_up_instructions" class="db-textarea" placeholder="Instructions for next visit…" rows="2"></textarea>
            </div>
          </div>

          <div v-if="consultationError" class="db-error-panel" style="margin-bottom:12px;">
            <span>{{ consultationError }}</span>
          </div>

          <div class="section-footer">
            <div v-if="consultationSaved" class="success-msg">✅ Consultation saved!</div>
            <button class="db-btn db-btn--primary" :disabled="savingConsultation" @click="saveConsultation">
              {{ savingConsultation ? 'Saving…' : '💾 Save Consultation' }}
            </button>
          </div>
        </div>

        <!-- SECTION: Medical History -->
        <div class="db-card consult-section">
          <div class="section-head">
            <span class="section-icon">📋</span>
            <h2 class="db-section-title">Add Medical History Record</h2>
            <button
              class="db-btn db-btn--ghost"
              style="margin-left:auto;"
              @click="showHistoryForm = !showHistoryForm"
            >
              {{ showHistoryForm ? '▲ Collapse' : '+ Add Record' }}
            </button>
          </div>

          <div v-if="historySaved" class="success-msg" style="margin-bottom: 12px;">✅ History record saved!</div>

          <div v-if="showHistoryForm">
            <div class="form-grid-2">
              <div class="db-form-group">
                <label class="db-label">Medical Condition *</label>
                <input v-model="historyForm.medical_condition" type="text" class="db-input" placeholder="e.g. Hypertension" />
              </div>
              <div class="db-form-group">
                <label class="db-label">Record Type</label>
                <select v-model="historyForm.record_type" class="db-select">
                  <option>Medical Condition</option>
                  <option>Allergy</option>
                  <option>Chronic Disease</option>
                  <option>Surgery</option>
                  <option>Vaccination</option>
                  <option>Lab Result</option>
                  <option>Other</option>
                </select>
              </div>
              <div class="db-form-group">
                <label class="db-label">Status</label>
                <select v-model="historyForm.status" class="db-select">
                  <option>Active</option>
                  <option>Resolved</option>
                  <option>Chronic</option>
                  <option>Inactive</option>
                </select>
              </div>
              <div class="db-form-group">
                <label class="db-label">Severity</label>
                <select v-model="historyForm.severity" class="db-select">
                  <option value="">— Select —</option>
                  <option>Mild</option>
                  <option>Moderate</option>
                  <option>Severe</option>
                  <option>Critical</option>
                </select>
              </div>
              <div class="db-form-group" style="grid-column: 1 / -1;">
                <label class="db-label">Description</label>
                <textarea v-model="historyForm.description" class="db-textarea" placeholder="Additional notes…" rows="2"></textarea>
              </div>
              <div class="db-form-group">
                <label class="db-label">Symptoms</label>
                <input v-model="historyForm.symptoms" type="text" class="db-input" placeholder="Reported symptoms" />
              </div>
              <div class="db-form-group">
                <label class="db-label">Allergies</label>
                <input v-model="historyForm.allergies" type="text" class="db-input" placeholder="Known allergies" />
              </div>
            </div>

            <div v-if="historyError" class="db-error-panel" style="margin-bottom:12px;">{{ historyError }}</div>

            <div class="section-footer">
              <button class="db-btn db-btn--primary" :disabled="savingHistory" @click="saveHistory">
                {{ savingHistory ? 'Saving…' : '💾 Save History Record' }}
              </button>
            </div>
          </div>
        </div>

        <!-- SECTION: Prescription -->
        <div class="db-card consult-section">
          <div class="section-head">
            <span class="section-icon">💊</span>
            <h2 class="db-section-title">Prescription</h2>
          </div>

          <!-- No prescription yet -->
          <div v-if="!prescription" class="no-prescription">
            <p>No prescription created for this appointment yet.</p>
            <div v-if="prescriptionError" class="db-error-panel" style="margin-bottom:12px;">{{ prescriptionError }}</div>
            <button class="db-btn db-btn--primary" :disabled="creatingPrescription" @click="createPrescription">
              {{ creatingPrescription ? 'Creating…' : '+ Create Prescription' }}
            </button>
          </div>

          <!-- Prescription exists -->
          <div v-else>
            <div class="prescription-info">
              <span :class="statusClass(prescription.status)">{{ prescription.status || 'Active' }}</span>
              <span style="font-size:12px; color:#64748b;">ID: {{ prescription.name }}</span>
              <div style="margin-left:auto; display:flex; gap:8px;">
                <button class="db-btn db-btn--secondary icon-btn" title="Edit Prescription" @click="openEditPrxModal">
                  ✏️ Edit
                </button>
                <button class="db-btn db-btn--danger icon-btn" title="Delete Prescription" @click="openDeletePrxModal">
                  🗑️ Delete
                </button>
              </div>
            </div>

            <!-- Prescription detail (diagnosis/instructions) -->
            <div v-if="prescription.diagnosis || prescription.instructions || prescription.follow_up_date" class="prx-detail-box">
              <div v-if="prescription.diagnosis" class="prx-detail-row">
                <span class="prx-detail-label">Diagnosis</span>
                <span class="prx-detail-val">{{ prescription.diagnosis }}</span>
              </div>
              <div v-if="prescription.instructions" class="prx-detail-row">
                <span class="prx-detail-label">Instructions</span>
                <span class="prx-detail-val">{{ prescription.instructions }}</span>
              </div>
              <div v-if="prescription.follow_up_date" class="prx-detail-row">
                <span class="prx-detail-label">Follow-up</span>
                <span class="prx-detail-val">{{ formatDate(prescription.follow_up_date) }}</span>
              </div>
              <div v-if="prescription.notes" class="prx-detail-row">
                <span class="prx-detail-label">Notes</span>
                <span class="prx-detail-val">{{ prescription.notes }}</span>
              </div>
            </div>

            <!-- Prescribed medicines list -->
            <div class="meds-header">
              <h3 class="meds-title">Prescribed Medicines</h3>
            </div>

            <div v-if="loadingMedicines" style="margin-bottom:16px;">
              <div class="db-skeleton" style="height:60px; border-radius:8px;"></div>
            </div>
            <div v-else-if="prescribedMedicines.length === 0" class="no-meds">
              No medicines added yet.
            </div>
            <div v-else class="prescribed-meds">
              <div v-for="m in prescribedMedicines" :key="m.name" class="prx-med-item">
                <div class="prx-med-left">
                  <div class="prx-med-name">{{ m.prescribed_medicine_name || m.medicine_name }}</div>
                  <div class="prx-med-meta">
                    <span>{{ m.dosage }}</span>
                    <span>· {{ m.frequency }}</span>
                    <span>· {{ m.route }}</span>
                    <span>· {{ m.start_date }} → {{ m.end_date }}</span>
                  </div>
                  <div v-if="m.instructions" class="prx-med-note">{{ m.instructions }}</div>
                </div>
                <div class="prx-med-right">
                  <span :class="statusClass(m.status)">{{ m.status }}</span>
                  <button class="icon-action-btn edit-btn" title="Edit medicine" @click="openEditMedModal(m)">✏️</button>
                  <button class="icon-action-btn delete-btn" title="Remove medicine" @click="openDeleteMedModal(m)">🗑️</button>
                </div>
              </div>
            </div>

            <!-- Add medicine form -->
            <div class="add-med-section">
              <h3 class="add-med-title">Add Medicine</h3>

              <!-- Medicine search -->
              <div class="db-form-group" style="position:relative;">
                <label class="db-label">Search Medicine</label>
                <div class="med-search-wrap">
                  <input
                    v-model="medicineSearch"
                    @input="searchMedicines"
                    type="text"
                    class="db-input"
                    placeholder="Type medicine name…"
                  />
                  <div v-if="medicineResults.length > 0" class="med-dropdown">
                    <div
                      v-for="med in medicineResults"
                      :key="med.name"
                      class="med-dropdown-item"
                      @click="selectMedicine(med)"
                    >
                      <div class="med-dropdown-name">{{ med.medicine_name }}</div>
                      <div class="med-dropdown-sub">
                        {{ med.generic_name }}
                        <span v-if="med.strength"> · {{ med.strength }}</span>
                        <span v-if="med.dosage_form"> · {{ med.dosage_form }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div v-if="showMedicineForm" class="med-form-fields">
                <div class="form-grid-3">
                  <div class="db-form-group">
                    <label class="db-label">Dosage *</label>
                    <input v-model="medForm.dosage" type="text" class="db-input" placeholder="e.g. 500mg" />
                  </div>
                  <div class="db-form-group">
                    <label class="db-label">Route</label>
                    <select v-model="medForm.route" class="db-select">
                      <option>Oral</option>
                      <option>Topical</option>
                      <option>Intravenous</option>
                      <option>Intramuscular</option>
                      <option>Subcutaneous</option>
                      <option>Inhaled</option>
                      <option>Nasal</option>
                      <option>Ophthalmic</option>
                      <option>Rectal</option>
                    </select>
                  </div>
                  <div class="db-form-group">
                    <label class="db-label">Frequency *</label>
                    <select v-model="medForm.frequency" class="db-select">
                      <option>Once Daily</option>
                      <option>Twice Daily</option>
                      <option>Three Times Daily</option>
                      <option>Four Times Daily</option>
                      <option>Every 6 Hours</option>
                      <option>Every 8 Hours</option>
                      <option>Every 12 Hours</option>
                      <option>As Needed</option>
                      <option>Weekly</option>
                    </select>
                  </div>
                  <div class="db-form-group">
                    <label class="db-label">Start Date *</label>
                    <input v-model="medForm.start_date" type="date" class="db-input" />
                  </div>
                  <div class="db-form-group">
                    <label class="db-label">End Date *</label>
                    <input v-model="medForm.end_date" type="date" class="db-input" />
                  </div>
                </div>

                <!-- Dose times -->
                <div v-if="freqDoseTimes(medForm.frequency) > 0" class="dose-times-grid">
                  <label class="db-label" style="grid-column: 1/-1;">Dose Times (for reminders)</label>
                  <input v-if="freqDoseTimes(medForm.frequency) >= 1" v-model="medForm.dose_time_1" type="time" class="db-input" placeholder="Dose 1" />
                  <input v-if="freqDoseTimes(medForm.frequency) >= 2" v-model="medForm.dose_time_2" type="time" class="db-input" placeholder="Dose 2" />
                  <input v-if="freqDoseTimes(medForm.frequency) >= 3" v-model="medForm.dose_time_3" type="time" class="db-input" placeholder="Dose 3" />
                  <input v-if="freqDoseTimes(medForm.frequency) >= 4" v-model="medForm.dose_time_4" type="time" class="db-input" placeholder="Dose 4" />
                </div>

                <div class="db-form-group">
                  <label class="db-label">Special Instructions</label>
                  <input v-model="medForm.instructions" type="text" class="db-input" placeholder="e.g. Take with food, avoid alcohol…" />
                </div>

                <div v-if="addMedError" class="db-error-panel" style="margin-bottom:12px;">{{ addMedError }}</div>

                <div style="display:flex; gap:10px;">
                  <button class="db-btn db-btn--primary" :disabled="addingMedicine" @click="addMedicine">
                    {{ addingMedicine ? 'Adding…' : '+ Add Medicine & Schedule Reminders' }}
                  </button>
                  <button class="db-btn db-btn--secondary" @click="showMedicineForm = false; medicineSearch = ''; selectedMedicine = null">
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- ======= EDIT PRESCRIPTION MODAL ======= -->
    <div v-if="showEditPrxModal" class="modal-overlay" @click.self="showEditPrxModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <h3 class="modal-title">✏️ Edit Prescription</h3>
          <button class="modal-close" @click="showEditPrxModal = false">✕</button>
        </div>
        <div class="modal-body">
          <div class="db-form-group">
            <label class="db-label">Diagnosis</label>
            <textarea v-model="editPrxForm.diagnosis" class="db-textarea" rows="2" placeholder="Diagnosis…"></textarea>
          </div>
          <div class="db-form-group">
            <label class="db-label">Instructions</label>
            <textarea v-model="editPrxForm.instructions" class="db-textarea" rows="2" placeholder="Patient instructions…"></textarea>
          </div>
          <div class="form-grid-2">
            <div class="db-form-group">
              <label class="db-label">Follow-up Date</label>
              <input v-model="editPrxForm.follow_up_date" type="date" class="db-input" />
            </div>
            <div class="db-form-group">
              <label class="db-label">Status</label>
              <select v-model="editPrxForm.status" class="db-select">
                <option>Active</option>
                <option>Completed</option>
                <option>Cancelled</option>
              </select>
            </div>
          </div>
          <div class="db-form-group">
            <label class="db-label">Notes</label>
            <textarea v-model="editPrxForm.notes" class="db-textarea" rows="2" placeholder="Additional notes…"></textarea>
          </div>
          <div v-if="editPrxError" class="db-error-panel">{{ editPrxError }}</div>
        </div>
        <div class="modal-footer">
          <button class="db-btn db-btn--secondary" @click="showEditPrxModal = false">Cancel</button>
          <button class="db-btn db-btn--primary" :disabled="editingPrx" @click="handleEditPrescription">
            {{ editingPrx ? 'Saving…' : '💾 Save Changes' }}
          </button>
        </div>
      </div>
    </div>

    <!-- ======= DELETE PRESCRIPTION MODAL ======= -->
    <div v-if="showDeletePrxModal" class="modal-overlay" @click.self="showDeletePrxModal = false">
      <div class="modal-card modal-card--sm">
        <div class="modal-header">
          <h3 class="modal-title">🗑️ Delete Prescription</h3>
          <button class="modal-close" @click="showDeletePrxModal = false">✕</button>
        </div>
        <div class="modal-body">
          <p class="modal-confirm-text">
            Are you sure you want to delete prescription <strong>{{ prescription?.name }}</strong>?
            This will also remove all associated medicines and reminders.
          </p>
          <div v-if="deletePrxError" class="db-error-panel">{{ deletePrxError }}</div>
        </div>
        <div class="modal-footer">
          <button class="db-btn db-btn--secondary" @click="showDeletePrxModal = false">Cancel</button>
          <button class="db-btn db-btn--danger" :disabled="deletingPrx" @click="handleDeletePrescription">
            {{ deletingPrx ? 'Deleting…' : '🗑️ Delete Prescription' }}
          </button>
        </div>
      </div>
    </div>

    <!-- ======= EDIT MEDICINE MODAL ======= -->
    <div v-if="showEditMedModal" class="modal-overlay" @click.self="showEditMedModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <h3 class="modal-title">✏️ Edit Medicine — {{ editMedForm.medicine_name }}</h3>
          <button class="modal-close" @click="showEditMedModal = false">✕</button>
        </div>
        <div class="modal-body">
          <div class="form-grid-3">
            <div class="db-form-group">
              <label class="db-label">Dosage</label>
              <input v-model="editMedForm.dosage" type="text" class="db-input" placeholder="e.g. 500mg" />
            </div>
            <div class="db-form-group">
              <label class="db-label">Route</label>
              <select v-model="editMedForm.route" class="db-select">
                <option>Oral</option>
                <option>Topical</option>
                <option>Intravenous</option>
                <option>Intramuscular</option>
                <option>Subcutaneous</option>
                <option>Inhaled</option>
                <option>Nasal</option>
                <option>Ophthalmic</option>
                <option>Rectal</option>
              </select>
            </div>
            <div class="db-form-group">
              <label class="db-label">Frequency</label>
              <select v-model="editMedForm.frequency" class="db-select">
                <option>Once Daily</option>
                <option>Twice Daily</option>
                <option>Three Times Daily</option>
                <option>Four Times Daily</option>
                <option>Every 6 Hours</option>
                <option>Every 8 Hours</option>
                <option>Every 12 Hours</option>
                <option>As Needed</option>
                <option>Weekly</option>
              </select>
            </div>
            <div class="db-form-group">
              <label class="db-label">Start Date</label>
              <input v-model="editMedForm.start_date" type="date" class="db-input" />
            </div>
            <div class="db-form-group">
              <label class="db-label">End Date</label>
              <input v-model="editMedForm.end_date" type="date" class="db-input" />
            </div>
            <div class="db-form-group">
              <label class="db-label">Status</label>
              <select v-model="editMedForm.status" class="db-select">
                <option>Active</option>
                <option>Completed</option>
                <option>Discontinued</option>
              </select>
            </div>
          </div>
          <div v-if="freqDoseTimes(editMedForm.frequency) > 0" class="dose-times-grid" style="margin-top:12px;">
            <label class="db-label" style="grid-column: 1/-1;">Dose Times</label>
            <input v-if="freqDoseTimes(editMedForm.frequency) >= 1" v-model="editMedForm.dose_time_1" type="time" class="db-input" />
            <input v-if="freqDoseTimes(editMedForm.frequency) >= 2" v-model="editMedForm.dose_time_2" type="time" class="db-input" />
            <input v-if="freqDoseTimes(editMedForm.frequency) >= 3" v-model="editMedForm.dose_time_3" type="time" class="db-input" />
            <input v-if="freqDoseTimes(editMedForm.frequency) >= 4" v-model="editMedForm.dose_time_4" type="time" class="db-input" />
          </div>
          <div class="db-form-group" style="margin-top:12px;">
            <label class="db-label">Special Instructions</label>
            <input v-model="editMedForm.instructions" type="text" class="db-input" placeholder="e.g. Take with food" />
          </div>
          <div v-if="editMedError" class="db-error-panel" style="margin-top:12px;">{{ editMedError }}</div>
        </div>
        <div class="modal-footer">
          <button class="db-btn db-btn--secondary" @click="showEditMedModal = false">Cancel</button>
          <button class="db-btn db-btn--primary" :disabled="editingMed" @click="handleEditMedicine">
            {{ editingMed ? 'Saving…' : '💾 Save Changes' }}
          </button>
        </div>
      </div>
    </div>

    <!-- ======= DELETE MEDICINE MODAL ======= -->
    <div v-if="showDeleteMedModal" class="modal-overlay" @click.self="showDeleteMedModal = false">
      <div class="modal-card modal-card--sm">
        <div class="modal-header">
          <h3 class="modal-title">🗑️ Remove Medicine</h3>
          <button class="modal-close" @click="showDeleteMedModal = false">✕</button>
        </div>
        <div class="modal-body">
          <p class="modal-confirm-text">
            Remove <strong>{{ selectedMedForDelete?.prescribed_medicine_name || selectedMedForDelete?.medicine_name }}</strong> from this prescription? Associated reminders will also be deleted.
          </p>
          <div v-if="deleteMedError" class="db-error-panel">{{ deleteMedError }}</div>
        </div>
        <div class="modal-footer">
          <button class="db-btn db-btn--secondary" @click="showDeleteMedModal = false">Cancel</button>
          <button class="db-btn db-btn--danger" :disabled="deletingMed" @click="handleDeleteMedicine">
            {{ deletingMed ? 'Removing…' : '🗑️ Remove Medicine' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.db-page {
  min-height: 100vh;
  padding: 32px 32px 64px;
  background:
    radial-gradient(circle at 10% 8%, rgba(13, 148, 136, 0.08), transparent 32%),
    radial-gradient(circle at 90% 12%, rgba(37, 99, 235, 0.06), transparent 30%),
    #f4f7fb;
  color: #0f172a;
}

.db-container {
  max-width: 1000px;
  margin: 0 auto;
}

.back-btn {
  margin-bottom: 24px;
}

.appt-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 28px;
  flex-wrap: wrap;
}

.appt-header-meta {
  font-size: 13px;
  color: #64748b;
  margin-top: 4px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.consult-section {
  margin-bottom: 24px;
}

.section-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.section-icon {
  font-size: 22px;
}

.form-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.form-grid-3 {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
}

.dose-times-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 14px;
}

.section-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f1f5f9;
}

.success-msg {
  font-size: 13px;
  color: #059669;
  font-weight: 600;
}

/* Prescription */
.no-prescription {
  padding: 20px 0;
  text-align: center;
  color: #64748b;
  font-size: 13px;
}

.no-prescription p {
  margin-bottom: 14px;
}

.prescription-info {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.prx-detail-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px 16px;
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.prx-detail-row {
  display: flex;
  gap: 8px;
  font-size: 12px;
}

.prx-detail-label {
  color: #94a3b8;
  font-weight: 600;
  min-width: 90px;
  flex-shrink: 0;
}

.prx-detail-val {
  color: #334155;
}

.meds-header {
  margin-bottom: 12px;
}

.meds-title {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
}

.no-meds {
  font-size: 13px;
  color: #94a3b8;
  text-align: center;
  padding: 16px;
  border: 1px dashed #e2e8f0;
  border-radius: 8px;
  margin-bottom: 16px;
}

.prescribed-meds {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 20px;
}

.prx-med-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
  transition: border-color 0.15s;
}

.prx-med-item:hover {
  border-color: #cbd5e1;
}

.prx-med-right {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.icon-action-btn {
  background: none;
  border: 1px solid transparent;
  border-radius: 6px;
  padding: 3px 7px;
  cursor: pointer;
  font-size: 13px;
  transition: background 0.15s, border-color 0.15s;
  line-height: 1.4;
}

.icon-action-btn.edit-btn:hover {
  background: #eff6ff;
  border-color: #bfdbfe;
}

.icon-action-btn.delete-btn:hover {
  background: #fef2f2;
  border-color: #fecaca;
}

.icon-btn {
  font-size: 12px;
  padding: 5px 10px;
}

.prx-med-name {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 3px;
}

.prx-med-meta {
  font-size: 11px;
  color: #64748b;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.prx-med-note {
  font-size: 11px;
  color: #94a3b8;
  font-style: italic;
  margin-top: 3px;
}

/* Add medicine */
.add-med-section {
  border-top: 1px solid #e2e8f0;
  padding-top: 20px;
  margin-top: 8px;
}

.add-med-title {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 14px;
}

.med-search-wrap {
  position: relative;
}

.med-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
  z-index: 50;
  max-height: 260px;
  overflow-y: auto;
}

.med-dropdown-item {
  padding: 10px 14px;
  cursor: pointer;
  transition: background 0.1s;
  border-bottom: 1px solid #f1f5f9;
}

.med-dropdown-item:last-child { border-bottom: none; }
.med-dropdown-item:hover { background: #f0fdfa; }

.med-dropdown-name {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}

.med-dropdown-sub {
  font-size: 11px;
  color: #64748b;
  margin-top: 2px;
}

.med-form-fields {
  margin-top: 16px;
  padding: 16px;
  background: #f8fafc;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.48);
  backdrop-filter: blur(3px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
  padding: 20px;
  animation: fadeIn 0.15s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.20);
  width: 100%;
  max-width: 580px;
  max-height: 90vh;
  overflow-y: auto;
  animation: slideUp 0.2s ease;
}

.modal-card--sm {
  max-width: 420px;
}

@keyframes slideUp {
  from { transform: translateY(16px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 0;
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 16px;
}

.modal-title {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
}

.modal-close {
  background: none;
  border: none;
  cursor: pointer;
  color: #94a3b8;
  font-size: 18px;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background 0.15s;
}

.modal-close:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.modal-body {
  padding: 20px 24px;
}

.modal-confirm-text {
  color: #475569;
  font-size: 14px;
  line-height: 1.6;
  margin: 0;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 24px 20px;
  border-top: 1px solid #f1f5f9;
}

/* Danger button */
.db-btn--danger {
  background: #ef4444;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 8px 18px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.db-btn--danger:hover:not(:disabled) {
  background: #dc2626;
}

.db-btn--danger:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .form-grid-2, .form-grid-3 { grid-template-columns: 1fr; }
  .dose-times-grid { grid-template-columns: 1fr 1fr; }
  .db-page { padding: 16px 16px 48px; }
}
</style>
