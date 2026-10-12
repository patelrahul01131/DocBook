<script setup>
import { ref, onMounted, computed, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { call } from '../../api'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const records = ref([])
const loading = ref(false)
const error = ref(null)
const activeTab = ref('all')
const showAddModal = ref(false)
const searchQuery = ref('')

const form = reactive({
  medical_condition: '',
  description: '',
  symptoms: '',
  allergies: '',
  current_medications: '',
  past_treatments: '',
  record_type: 'Medical Condition',
  status: 'Active',
  severity: '',
  notes: '',
})
const saving = ref(false)
const saveError = ref(null)

// Edit modal
const showEditModal = ref(false)
const editingRecord = ref(false)
const editError = ref(null)
const selectedRecord = ref(null)
const editForm = reactive({
  name: '',
  medical_condition: '',
  description: '',
  symptoms: '',
  allergies: '',
  current_medications: '',
  past_treatments: '',
  record_type: 'Medical Condition',
  status: 'Active',
  severity: '',
  notes: '',
})

// Delete modal
const showDeleteModal = ref(false)
const deletingRecord = ref(false)
const deleteError = ref(null)
const recordForDelete = ref(null)

const tabs = [
  { key: 'all', label: 'All Records' },
  { key: 'Active', label: 'Active' },
  { key: 'Resolved', label: 'Resolved' },
  { key: 'Inactive', label: 'Inactive' },
]

const filteredRecords = computed(() => {
  let list = records.value
  if (activeTab.value !== 'all') {
    list = list.filter(r => r.status === activeTab.value)
  }
  const q = searchQuery.value.trim().toLowerCase()
  if (q) {
    list = list.filter(r =>
      (r.medical_condition || '').toLowerCase().includes(q) ||
      (r.condition || '').toLowerCase().includes(q) ||
      (r.description || '').toLowerCase().includes(q) ||
      (r.symptoms || '').toLowerCase().includes(q) ||
      (r.record_type || '').toLowerCase().includes(q)
    )
  }
  return list
})

async function fetchHistory() {
  loading.value = true
  error.value = null
  try {
    const res = await call('docbook.api.medical_history.get_my_medical_history')
    records.value = Array.isArray(res) ? res : []
  } catch (e) {
    error.value = e.message || 'Unable to load medical history.'
  } finally {
    loading.value = false
  }
}

// Add record
function openAddModal() {
  saveError.value = null
  Object.assign(form, {
    medical_condition: '', description: '', symptoms: '', allergies: '',
    current_medications: '', past_treatments: '', record_type: 'Medical Condition',
    status: 'Active', severity: '', notes: '',
  })
  showAddModal.value = true
}

async function saveRecord() {
  if (!form.medical_condition) {
    saveError.value = 'Medical condition is required.'
    return
  }
  saving.value = true
  saveError.value = null
  try {
    const patient = auth.user?.profile_name || auth.user?.name || auth.user?.email
    await call('docbook.api.medical_history.create_medical_history_record', {
      patient,
      record_date: new Date().toISOString().slice(0, 10),
      ...form,
    })
    showAddModal.value = false
    await fetchHistory()
  } catch (e) {
    saveError.value = e.message || 'Failed to save record.'
  } finally {
    saving.value = false
  }
}

// Edit record
function openEditModal(record) {
  editError.value = null
  selectedRecord.value = record
  Object.assign(editForm, {
    name: record.name,
    medical_condition: record.medical_condition || record.condition || '',
    description: record.description || '',
    symptoms: record.symptoms || '',
    allergies: record.allergies || '',
    current_medications: record.current_medications || '',
    past_treatments: record.past_treatments || '',
    record_type: record.record_type || 'Medical Condition',
    status: record.status || 'Active',
    severity: record.severity || '',
    notes: record.treatment_notes || record.notes || '',
  })
  showEditModal.value = true
}

async function handleEditRecord() {
  if (!editForm.medical_condition) {
    editError.value = 'Medical condition is required.'
    return
  }
  editingRecord.value = true
  editError.value = null
  try {
    await call('docbook.api.medical_history.update_medical_history_record', {
      record_name: editForm.name,
      medical_condition: editForm.medical_condition,
      condition: editForm.medical_condition,
      description: editForm.description,
      symptoms: editForm.symptoms,
      allergies: editForm.allergies,
      current_medications: editForm.current_medications,
      past_treatments: editForm.past_treatments,
      record_type: editForm.record_type,
      status: editForm.status,
      severity: editForm.severity,
      treatment_notes: editForm.notes,
    })
    showEditModal.value = false
    await fetchHistory()
  } catch (e) {
    editError.value = e.message || 'Failed to update record.'
  } finally {
    editingRecord.value = false
  }
}

// Delete record
function openDeleteModal(record) {
  deleteError.value = null
  recordForDelete.value = record
  showDeleteModal.value = true
}

async function handleDeleteRecord() {
  if (!recordForDelete.value) return
  deletingRecord.value = true
  deleteError.value = null
  try {
    await call('docbook.api.medical_history.delete_medical_history_record', {
      record_name: recordForDelete.value.name,
    })
    showDeleteModal.value = false
    recordForDelete.value = null
    await fetchHistory()
  } catch (e) {
    deleteError.value = e.message || 'Failed to delete record.'
  } finally {
    deletingRecord.value = false
  }
}

function formatDate(d) {
  if (!d) return '—'
  return new Date(`${d}T00:00:00`).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
}

function statusClass(s) {
  return `db-badge db-badge--${(s || '').toLowerCase()}`
}

function severityClass(s) {
  const map = { 'Mild': 'mild', 'Moderate': 'moderate', 'Severe': 'severe', 'Critical': 'critical' }
  return `severity-chip severity-${map[s] || 'mild'}`
}

onMounted(fetchHistory)
</script>

<template>
  <div class="mh-page">
    <div class="mh-container">
      <!-- Header -->
      <header class="mh-header">
        <div>
          <div class="mh-eyebrow">PATIENT PORTAL</div>
          <h1 class="mh-title">Medical History</h1>
          <p class="mh-subtitle">Your health records, conditions, and medical history.</p>
        </div>
        <div class="mh-header-actions">
          <button class="mh-btn mh-btn--primary" @click="openAddModal">
            + Add Record
          </button>
          <button class="mh-btn mh-btn--secondary" :disabled="loading" @click="fetchHistory">
            ↻ Refresh
          </button>
        </div>
      </header>

      <!-- Search + Tabs -->
      <div class="mh-controls">
        <input
          v-model="searchQuery"
          class="mh-search"
          type="text"
          placeholder="🔍 Search records…"
        />
        <div class="mh-tabs">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="mh-tab"
            :class="{ active: activeTab === tab.key }"
            @click="activeTab = tab.key"
          >
            {{ tab.label }}
            <span v-if="tab.key !== 'all'" class="mh-tab-count">
              {{ records.filter(r => r.status === tab.key).length }}
            </span>
          </button>
        </div>
      </div>

      <!-- Error -->
      <div v-if="error" class="mh-error">
        <span>⚠️</span> {{ error }}
        <button class="mh-btn mh-btn--secondary" @click="fetchHistory">Retry</button>
      </div>

      <!-- Loading skeleton -->
      <div v-else-if="loading" class="mh-grid">
        <div v-for="i in 4" :key="i" class="mh-card skeleton-card">
          <div class="skeleton-line wide"></div>
          <div class="skeleton-line medium" style="margin-top:10px;"></div>
          <div class="skeleton-line short" style="margin-top:8px;"></div>
        </div>
      </div>

      <!-- Empty -->
      <div v-else-if="filteredRecords.length === 0" class="mh-empty">
        <div class="mh-empty-icon">📋</div>
        <h3>No records found</h3>
        <p v-if="activeTab === 'all' && !searchQuery">Start by adding your first medical history record.</p>
        <p v-else>No records match your current filter.</p>
        <button v-if="activeTab === 'all'" class="mh-btn mh-btn--primary" style="margin-top:16px;" @click="openAddModal">+ Add First Record</button>
      </div>

      <!-- Records grid -->
      <div v-else class="mh-grid">
        <article
          v-for="record in filteredRecords"
          :key="record.name"
          class="mh-card"
        >
          <div class="mh-card-header">
            <div class="mh-card-title-row">
              <h3 class="mh-condition">{{ record.medical_condition || record.condition || 'Unknown condition' }}</h3>
              <span :class="statusClass(record.status)">{{ record.status }}</span>
            </div>
            <p class="mh-record-type">{{ record.record_type || 'Medical Condition' }}</p>
          </div>

          <div v-if="record.description" class="mh-description">{{ record.description }}</div>

          <div class="mh-meta-grid">
            <div v-if="record.severity" class="mh-meta-item">
              <span class="mh-meta-label">Severity</span>
              <span :class="severityClass(record.severity)">{{ record.severity }}</span>
            </div>
            <div v-if="record.symptoms" class="mh-meta-item">
              <span class="mh-meta-label">Symptoms</span>
              <span class="mh-meta-val">{{ record.symptoms }}</span>
            </div>
            <div v-if="record.allergies" class="mh-meta-item">
              <span class="mh-meta-label">Allergies</span>
              <span class="mh-meta-val">{{ record.allergies }}</span>
            </div>
            <div v-if="record.current_medications" class="mh-meta-item">
              <span class="mh-meta-label">Medications</span>
              <span class="mh-meta-val">{{ record.current_medications }}</span>
            </div>
          </div>

          <div class="mh-card-footer">
            <div class="mh-footer-left">
              <span>📅</span>
              <span>{{ formatDate(record.record_date) }}</span>
              <span v-if="record.recorded_by_name" class="mh-recorded-by">by {{ record.recorded_by_name }}</span>
            </div>
            <div class="mh-footer-actions">
              <button class="mh-action-btn edit" title="Edit record" @click="openEditModal(record)">✏️</button>
              <button class="mh-action-btn delete" title="Delete record" @click="openDeleteModal(record)">🗑️</button>
            </div>
          </div>
        </article>
      </div>

      <!-- Disclaimer -->
      <p class="mh-disclaimer">
        ℹ️ Medical history records can be added and edited by you or your healthcare providers. Contact your doctor to request corrections.
      </p>
    </div>

    <!-- ======= ADD RECORD MODAL ======= -->
    <div v-if="showAddModal" class="modal-overlay" @click.self="showAddModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <h3 class="modal-title">+ Add Medical History Record</h3>
          <button class="modal-close" @click="showAddModal = false">✕</button>
        </div>
        <div class="modal-body">
          <div class="form-grid-2">
            <div class="db-form-group">
              <label class="db-label">Medical Condition *</label>
              <input v-model="form.medical_condition" type="text" class="db-input" placeholder="e.g. Hypertension" />
            </div>
            <div class="db-form-group">
              <label class="db-label">Record Type</label>
              <select v-model="form.record_type" class="db-select">
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
              <select v-model="form.status" class="db-select">
                <option>Active</option>
                <option>Resolved</option>
                <option>Chronic</option>
                <option>Inactive</option>
              </select>
            </div>
            <div class="db-form-group">
              <label class="db-label">Severity</label>
              <select v-model="form.severity" class="db-select">
                <option value="">— Select —</option>
                <option>Mild</option>
                <option>Moderate</option>
                <option>Severe</option>
                <option>Critical</option>
              </select>
            </div>
            <div class="db-form-group" style="grid-column: 1 / -1;">
              <label class="db-label">Description</label>
              <textarea v-model="form.description" class="db-textarea" rows="2" placeholder="Details about the condition…"></textarea>
            </div>
            <div class="db-form-group">
              <label class="db-label">Symptoms</label>
              <input v-model="form.symptoms" type="text" class="db-input" placeholder="Reported symptoms" />
            </div>
            <div class="db-form-group">
              <label class="db-label">Allergies</label>
              <input v-model="form.allergies" type="text" class="db-input" placeholder="Known allergies" />
            </div>
            <div class="db-form-group">
              <label class="db-label">Current Medications</label>
              <input v-model="form.current_medications" type="text" class="db-input" placeholder="Current medications" />
            </div>
            <div class="db-form-group">
              <label class="db-label">Past Treatments</label>
              <input v-model="form.past_treatments" type="text" class="db-input" placeholder="Previous treatments" />
            </div>
          </div>
          <div v-if="saveError" class="mh-error" style="margin-top:12px;">⚠️ {{ saveError }}</div>
        </div>
        <div class="modal-footer">
          <button class="mh-btn mh-btn--secondary" @click="showAddModal = false">Cancel</button>
          <button class="mh-btn mh-btn--primary" :disabled="saving" @click="saveRecord">
            {{ saving ? 'Saving…' : '💾 Save Record' }}
          </button>
        </div>
      </div>
    </div>

    <!-- ======= EDIT RECORD MODAL ======= -->
    <div v-if="showEditModal" class="modal-overlay" @click.self="showEditModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <h3 class="modal-title">✏️ Edit Record</h3>
          <button class="modal-close" @click="showEditModal = false">✕</button>
        </div>
        <div class="modal-body">
          <div class="form-grid-2">
            <div class="db-form-group">
              <label class="db-label">Medical Condition *</label>
              <input v-model="editForm.medical_condition" type="text" class="db-input" />
            </div>
            <div class="db-form-group">
              <label class="db-label">Record Type</label>
              <select v-model="editForm.record_type" class="db-select">
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
              <select v-model="editForm.status" class="db-select">
                <option>Active</option>
                <option>Resolved</option>
                <option>Chronic</option>
                <option>Inactive</option>
              </select>
            </div>
            <div class="db-form-group">
              <label class="db-label">Severity</label>
              <select v-model="editForm.severity" class="db-select">
                <option value="">— Select —</option>
                <option>Mild</option>
                <option>Moderate</option>
                <option>Severe</option>
                <option>Critical</option>
              </select>
            </div>
            <div class="db-form-group" style="grid-column: 1 / -1;">
              <label class="db-label">Description</label>
              <textarea v-model="editForm.description" class="db-textarea" rows="2"></textarea>
            </div>
            <div class="db-form-group">
              <label class="db-label">Symptoms</label>
              <input v-model="editForm.symptoms" type="text" class="db-input" />
            </div>
            <div class="db-form-group">
              <label class="db-label">Allergies</label>
              <input v-model="editForm.allergies" type="text" class="db-input" />
            </div>
            <div class="db-form-group">
              <label class="db-label">Current Medications</label>
              <input v-model="editForm.current_medications" type="text" class="db-input" />
            </div>
            <div class="db-form-group">
              <label class="db-label">Past Treatments</label>
              <input v-model="editForm.past_treatments" type="text" class="db-input" />
            </div>
            <div class="db-form-group" style="grid-column: 1 / -1;">
              <label class="db-label">Notes</label>
              <textarea v-model="editForm.notes" class="db-textarea" rows="2" placeholder="Additional notes…"></textarea>
            </div>
          </div>
          <div v-if="editError" class="mh-error" style="margin-top:12px;">⚠️ {{ editError }}</div>
        </div>
        <div class="modal-footer">
          <button class="mh-btn mh-btn--secondary" @click="showEditModal = false">Cancel</button>
          <button class="mh-btn mh-btn--primary" :disabled="editingRecord" @click="handleEditRecord">
            {{ editingRecord ? 'Saving…' : '💾 Save Changes' }}
          </button>
        </div>
      </div>
    </div>

    <!-- ======= DELETE RECORD MODAL ======= -->
    <div v-if="showDeleteModal" class="modal-overlay" @click.self="showDeleteModal = false">
      <div class="modal-card modal-sm">
        <div class="modal-header">
          <h3 class="modal-title">🗑️ Delete Record</h3>
          <button class="modal-close" @click="showDeleteModal = false">✕</button>
        </div>
        <div class="modal-body">
          <p class="modal-confirm-text">
            Are you sure you want to permanently delete the record for
            <strong>{{ recordForDelete?.medical_condition || recordForDelete?.condition }}</strong>?
            This action cannot be undone.
          </p>
          <div v-if="deleteError" class="mh-error" style="margin-top:12px;">⚠️ {{ deleteError }}</div>
        </div>
        <div class="modal-footer">
          <button class="mh-btn mh-btn--secondary" @click="showDeleteModal = false">Cancel</button>
          <button class="mh-btn mh-btn--danger" :disabled="deletingRecord" @click="handleDeleteRecord">
            {{ deletingRecord ? 'Deleting…' : '🗑️ Delete Record' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.mh-page {
  min-height: 100vh;
  padding: 32px 32px 64px;
  background:
    radial-gradient(circle at 15% 10%, rgba(13, 148, 136, 0.06), transparent 30%),
    radial-gradient(circle at 85% 15%, rgba(139, 92, 246, 0.05), transparent 28%),
    #f4f7fb;
  font-family: 'Inter', system-ui, sans-serif;
  color: #0f172a;
}

.mh-container {
  max-width: 1100px;
  margin: 0 auto;
}

.mh-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 28px;
  flex-wrap: wrap;
}

.mh-eyebrow {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1.5px;
  color: #0d9488;
  text-transform: uppercase;
  margin-bottom: 6px;
}

.mh-title {
  font-size: 28px;
  font-weight: 800;
  color: #0f172a;
  margin: 0 0 4px;
}

.mh-subtitle {
  font-size: 14px;
  color: #64748b;
  margin: 0;
}

.mh-header-actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}

.mh-controls {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.mh-search {
  flex: 1;
  min-width: 180px;
  max-width: 320px;
  padding: 9px 14px;
  border: 1.5px solid #e2e8f0;
  border-radius: 10px;
  font-size: 13px;
  background: white;
  color: #0f172a;
  outline: none;
  transition: border-color 0.2s;
}

.mh-search:focus {
  border-color: #0d9488;
}

.mh-tabs {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.mh-tab {
  padding: 7px 14px;
  border-radius: 8px;
  border: 1.5px solid #e2e8f0;
  background: white;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  transition: all 0.15s;
  display: flex;
  align-items: center;
  gap: 5px;
}

.mh-tab:hover {
  border-color: #0d9488;
  color: #0d9488;
}

.mh-tab.active {
  background: #0d9488;
  border-color: #0d9488;
  color: white;
}

.mh-tab-count {
  background: rgba(255,255,255,0.25);
  border-radius: 10px;
  padding: 0 6px;
  font-size: 10px;
  font-weight: 700;
}

.mh-tab.active .mh-tab-count {
  background: rgba(255,255,255,0.3);
}

.mh-error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 10px;
  color: #dc2626;
  padding: 10px 16px;
  font-size: 13px;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.mh-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
  margin-bottom: 32px;
}

.mh-card {
  background: white;
  border: 1.5px solid #e8edf3;
  border-radius: 14px;
  padding: 20px;
  transition: box-shadow 0.2s, transform 0.2s, border-color 0.2s;
}

.mh-card:hover {
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.09);
  transform: translateY(-2px);
  border-color: #cbd5e1;
}

.skeleton-card {
  background: white;
  min-height: 140px;
}

.skeleton-line {
  height: 12px;
  background: linear-gradient(90deg, #f1f5f9 0%, #e2e8f0 50%, #f1f5f9 100%);
  background-size: 200% 100%;
  border-radius: 6px;
  animation: shimmer 1.4s infinite;
}

.skeleton-line.wide { width: 65%; }
.skeleton-line.medium { width: 45%; }
.skeleton-line.short { width: 30%; }

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

.mh-card-header {
  margin-bottom: 10px;
}

.mh-card-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 4px;
}

.mh-condition {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
  flex: 1;
}

.mh-record-type {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  color: #94a3b8;
  margin: 0;
}

.mh-description {
  font-size: 13px;
  color: #475569;
  line-height: 1.5;
  margin-bottom: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.mh-meta-grid {
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding: 12px 0;
  border-top: 1px solid #f1f5f9;
  border-bottom: 1px solid #f1f5f9;
  margin-bottom: 12px;
}

.mh-meta-item {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
  font-size: 12px;
}

.mh-meta-label {
  color: #94a3b8;
  flex-shrink: 0;
  font-weight: 500;
}

.mh-meta-val {
  color: #334155;
  font-weight: 500;
  text-align: right;
}

.severity-chip {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 20px;
  text-align: right;
}

.severity-mild { background: #dcfce7; color: #15803d; }
.severity-moderate { background: #fef9c3; color: #854d0e; }
.severity-severe { background: #fee2e2; color: #b91c1c; }
.severity-critical { background: #3b0764; color: #e9d5ff; }

.mh-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 11px;
  color: #94a3b8;
}

.mh-footer-left {
  display: flex;
  align-items: center;
  gap: 5px;
}

.mh-recorded-by {
  color: #64748b;
}

.mh-footer-actions {
  display: flex;
  gap: 4px;
}

.mh-action-btn {
  background: none;
  border: 1px solid transparent;
  border-radius: 6px;
  padding: 3px 8px;
  cursor: pointer;
  font-size: 13px;
  transition: background 0.15s, border-color 0.15s;
}

.mh-action-btn.edit:hover { background: #eff6ff; border-color: #bfdbfe; }
.mh-action-btn.delete:hover { background: #fef2f2; border-color: #fecaca; }

.mh-empty {
  text-align: center;
  padding: 48px 20px;
  color: #64748b;
}

.mh-empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.mh-empty h3 {
  font-size: 17px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 6px;
}

.mh-empty p {
  font-size: 13px;
}

.mh-disclaimer {
  margin-top: 32px;
  padding: 12px 16px;
  background: #f8fafc;
  border-radius: 8px;
  font-size: 12px;
  color: #64748b;
  border: 1px solid #e2e8f0;
}

/* Buttons */
.mh-btn {
  padding: 9px 18px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.mh-btn--primary {
  background: linear-gradient(135deg, #0d9488, #0891b2);
  color: white;
}

.mh-btn--primary:hover:not(:disabled) {
  background: linear-gradient(135deg, #0f766e, #0e7490);
  box-shadow: 0 4px 12px rgba(13, 148, 136, 0.3);
}

.mh-btn--secondary {
  background: white;
  border: 1.5px solid #e2e8f0;
  color: #475569;
}

.mh-btn--secondary:hover:not(:disabled) {
  border-color: #94a3b8;
  color: #0f172a;
}

.mh-btn--danger {
  background: #ef4444;
  color: white;
}

.mh-btn--danger:hover:not(:disabled) {
  background: #dc2626;
}

.mh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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
  max-width: 620px;
  max-height: 90vh;
  overflow-y: auto;
  animation: slideUp 0.2s ease;
}

.modal-sm {
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
  padding: 20px 24px 16px;
  border-bottom: 1px solid #f1f5f9;
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

.form-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

/* Reuse global input styles */
.db-form-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.db-label {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.6px;
}

.db-input, .db-select, .db-textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1.5px solid #e2e8f0;
  border-radius: 8px;
  font-size: 13px;
  color: #0f172a;
  background: white;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.db-input:focus, .db-select:focus, .db-textarea:focus {
  border-color: #0d9488;
}

.db-textarea {
  resize: vertical;
  line-height: 1.5;
}

/* Badge styles */
.db-badge { display: inline-flex; align-items: center; padding: 2px 10px; border-radius: 20px; font-size: 10px; font-weight: 700; letter-spacing: 0.5px; white-space: nowrap; text-transform: uppercase; }
.db-badge--active { background: #dcfce7; color: #15803d; }
.db-badge--resolved { background: #dbeafe; color: #1d4ed8; }
.db-badge--chronic { background: #fef3c7; color: #92400e; }
.db-badge--inactive { background: #f1f5f9; color: #64748b; }
.db-badge--pending { background: #fef9c3; color: #854d0e; }
.db-badge--completed { background: #dcfce7; color: #15803d; }
.db-badge--cancelled { background: #fee2e2; color: #b91c1c; }

@media (max-width: 640px) {
  .mh-header { flex-direction: column; align-items: flex-start; }
  .mh-grid { grid-template-columns: 1fr; }
  .form-grid-2 { grid-template-columns: 1fr; }
  .mh-page { padding: 16px 16px 48px; }
  .mh-controls { flex-direction: column; align-items: stretch; }
  .mh-search { max-width: 100%; }
}
</style>
