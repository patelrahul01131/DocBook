<script setup>
import { ref, onMounted, computed } from 'vue'
import { call } from '../../api'

const prescriptions = ref([])
const medicines = ref([])
const loading = ref(false)
const error = ref(null)
const selectedPrescription = ref(null)
const detailLoading = ref(false)
const detailError = ref(null)
const activeTab = ref('prescriptions')

const tabs = [
  { key: 'prescriptions', label: '📋 Prescriptions', icon: 'lucide-scroll' },
  { key: 'medicines', label: '💊 Medicines', icon: 'lucide-pill' },
]

const activeMedicines = computed(() =>
  medicines.value.filter(m => m.status === 'Active')
)

async function fetchData() {
  loading.value = true
  error.value = null
  try {
    const [prxRes, medRes] = await Promise.all([
      call('docbook.api.prescription.get_my_prescriptions'),
      call('docbook.api.prescription.get_my_prescription_medicines'),
    ])
    prescriptions.value = Array.isArray(prxRes) ? prxRes : []
    medicines.value = Array.isArray(medRes) ? medRes : []
  } catch (e) {
    error.value = e.message || 'Unable to load prescriptions.'
  } finally {
    loading.value = false
  }
}

async function openPrescription(prx) {
  detailLoading.value = true
  detailError.value = null
  selectedPrescription.value = { ...prx, medicines: null }
  try {
    const detail = await call('docbook.api.prescription.get_prescription_detail', {
      prescription_name: prx.name,
    })
    selectedPrescription.value = detail
  } catch (e) {
    detailError.value = e.message || 'Failed to load prescription details.'
  } finally {
    detailLoading.value = false
  }
}

function closeDetail() {
  selectedPrescription.value = null
  detailError.value = null
}

function formatDate(d) {
  if (!d) return '—'
  return new Date(`${d}T00:00:00`).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
}

function statusClass(s) {
  return `db-badge db-badge--${(s || 'draft').toLowerCase()}`
}

function getMedicineStatusClass(s) {
  return `db-badge db-badge--${(s || '').toLowerCase()}`
}

onMounted(fetchData)
</script>

<template>
  <div class="db-page">
    <div class="db-container">
      <!-- Header -->
      <header style="margin-bottom: 28px;">
        <div class="db-eyebrow">PATIENT PORTAL</div>
        <h1 class="db-page-title">Prescriptions</h1>
        <p class="db-section-subtitle">Your prescriptions and prescribed medicines from doctors.</p>
      </header>

      <!-- Error -->
      <div v-if="error" class="db-error-panel" style="margin-bottom: 24px;">
        <span style="font-size: 18px; flex-shrink:0;">⚠️</span>
        <span>{{ error }}</span>
        <button class="db-btn db-btn--secondary" style="margin-left:auto" @click="fetchData">Retry</button>
      </div>

      <!-- Tabs -->
      <div class="db-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="db-tab"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </div>

      <!-- PRESCRIPTIONS TAB -->
      <div v-if="activeTab === 'prescriptions'">
        <!-- Loading -->
        <div v-if="loading" class="prx-list">
          <div v-for="i in 3" :key="i" class="db-card" style="min-height:100px;">
            <div class="db-skeleton" style="height:14px; width:50%; margin-bottom:12px;"></div>
            <div class="db-skeleton" style="height:11px; width:70%; margin-bottom:8px;"></div>
            <div class="db-skeleton" style="height:11px; width:35%;"></div>
          </div>
        </div>

        <div v-else-if="prescriptions.length === 0" class="db-empty">
          <div class="db-empty-icon">📋</div>
          <h3>No prescriptions yet</h3>
          <p>Your doctor will add prescriptions after your consultations.</p>
        </div>

        <div v-else class="prx-list">
          <div
            v-for="prx in prescriptions"
            :key="prx.name"
            class="db-card prx-card"
            @click="openPrescription(prx)"
          >
            <div class="prx-row">
              <div class="prx-left">
                <div class="prx-icon">💊</div>
                <div>
                  <div class="prx-doctor">
                    Dr. {{ prx.doctor_name || prx.doctor }}
                    <span v-if="prx.doctor_specialty" class="prx-specialty">
                      — {{ prx.doctor_specialty }}
                    </span>
                  </div>
                  <div class="prx-date">Prescribed: {{ formatDate(prx.prescription_date) }}</div>
                  <div v-if="prx.diagnosis" class="prx-diagnosis">
                    <strong>Diagnosis:</strong> {{ prx.diagnosis }}
                  </div>
                </div>
              </div>
              <div class="prx-right">
                <span :class="statusClass(prx.status)">{{ prx.status }}</span>
                <span v-if="prx.follow_up_date" class="prx-followup">
                  Follow-up: {{ formatDate(prx.follow_up_date) }}
                </span>
                <span class="prx-view-link">View →</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- MEDICINES TAB -->
      <div v-if="activeTab === 'medicines'">
        <div v-if="loading" class="medicine-grid">
          <div v-for="i in 4" :key="i" class="db-card" style="min-height:120px;">
            <div class="db-skeleton" style="height:14px; width:65%; margin-bottom:12px;"></div>
            <div class="db-skeleton" style="height:11px; width:45%;"></div>
          </div>
        </div>

        <div v-else-if="medicines.length === 0" class="db-empty">
          <div class="db-empty-icon">💊</div>
          <h3>No prescribed medicines</h3>
          <p>Medicines prescribed by your doctor will appear here.</p>
        </div>

        <div v-else class="medicine-grid">
          <article
            v-for="med in medicines"
            :key="med.name"
            class="db-card med-card"
          >
            <div class="med-header">
              <div class="med-avatar">💊</div>
              <div>
                <div class="med-name">{{ med.prescribed_medicine_name || med.medicine_name }}</div>
                <div v-if="med.generic_name" class="med-generic">{{ med.generic_name }}</div>
              </div>
              <span :class="getMedicineStatusClass(med.status)">{{ med.status }}</span>
            </div>

            <div class="med-details">
              <div class="db-info-row">
                <span class="label">Dosage</span>
                <span class="value">{{ med.dosage || '—' }}</span>
              </div>
              <div class="db-info-row">
                <span class="label">Frequency</span>
                <span class="value">{{ med.frequency || '—' }}</span>
              </div>
              <div class="db-info-row">
                <span class="label">Route</span>
                <span class="value">{{ med.route || '—' }}</span>
              </div>
              <div class="db-info-row">
                <span class="label">Period</span>
                <span class="value">{{ formatDate(med.start_date) }} → {{ formatDate(med.end_date) }}</span>
              </div>
            </div>

            <div v-if="med.dose_time_1 || med.dose_time_2 || med.dose_time_3 || med.dose_time_4" class="dose-times">
              <div class="dose-label">Dose times:</div>
              <div class="dose-chips">
                <span v-if="med.dose_time_1" class="dose-chip">{{ med.dose_time_1.substring(0, 5) }}</span>
                <span v-if="med.dose_time_2" class="dose-chip">{{ med.dose_time_2.substring(0, 5) }}</span>
                <span v-if="med.dose_time_3" class="dose-chip">{{ med.dose_time_3.substring(0, 5) }}</span>
                <span v-if="med.dose_time_4" class="dose-chip">{{ med.dose_time_4.substring(0, 5) }}</span>
              </div>
            </div>

            <div v-if="med.instructions" class="med-instructions">
              📝 {{ med.instructions }}
            </div>

            <div v-if="med.uses" class="med-uses">
              <span style="font-size:10px; font-weight:600; color:#94a3b8; letter-spacing:0.8px; text-transform:uppercase;">Uses</span>
              <div style="font-size:12px; color:#475569; margin-top:4px;">{{ med.uses }}</div>
            </div>
          </article>
        </div>
      </div>

      <!-- Prescription Detail Drawer / Modal -->
      <div v-if="selectedPrescription" class="detail-overlay" @click.self="closeDetail">
        <div class="detail-drawer">
          <div class="drawer-header">
            <div>
              <div class="db-eyebrow">PRESCRIPTION DETAIL</div>
              <h2 class="drawer-title">
                Dr. {{ selectedPrescription.doctor_info?.full_name || selectedPrescription.doctor }}
              </h2>
              <div class="drawer-subtitle">
                {{ formatDate(selectedPrescription.prescription_date) }}
                <span v-if="selectedPrescription.doctor_info?.specialty">
                  · {{ selectedPrescription.doctor_info.specialty }}
                </span>
              </div>
            </div>
            <div class="drawer-header-right">
              <span :class="statusClass(selectedPrescription.status)">{{ selectedPrescription.status }}</span>
              <button class="db-btn db-btn--secondary" @click="closeDetail">✕ Close</button>
            </div>
          </div>

          <!-- Loading/Error in drawer -->
          <div v-if="detailLoading" style="padding: 24px;">
            <div class="db-skeleton" style="height:14px; width:60%; margin-bottom:12px;"></div>
            <div class="db-skeleton" style="height:14px; width:80%; margin-bottom:8px;"></div>
            <div class="db-skeleton" style="height:14px; width:45%;"></div>
          </div>
          <div v-else-if="detailError" class="db-error-panel" style="margin: 16px 0;">
            <span>{{ detailError }}</span>
          </div>

          <div v-else>
            <!-- Diagnosis + Instructions -->
            <div v-if="selectedPrescription.diagnosis" class="drawer-section">
              <div class="drawer-section-title">Diagnosis</div>
              <p class="drawer-text">{{ selectedPrescription.diagnosis }}</p>
            </div>

            <div v-if="selectedPrescription.instructions" class="drawer-section">
              <div class="drawer-section-title">Instructions</div>
              <p class="drawer-text">{{ selectedPrescription.instructions }}</p>
            </div>

            <div v-if="selectedPrescription.follow_up_date" class="followup-banner">
              📅 Follow-up scheduled: <strong>{{ formatDate(selectedPrescription.follow_up_date) }}</strong>
            </div>

            <!-- Medicines in prescription -->
            <div class="drawer-section">
              <div class="drawer-section-title">Prescribed Medicines</div>
              <div v-if="!selectedPrescription.medicines || selectedPrescription.medicines.length === 0" class="drawer-empty">
                No medicines attached to this prescription.
              </div>
              <div v-else class="prx-medicines">
                <div
                  v-for="m in selectedPrescription.medicines"
                  :key="m.name"
                  class="prx-medicine-card"
                >
                  <div class="prx-med-header">
                    <span class="prx-med-icon">💊</span>
                    <div class="prx-med-name">{{ m.prescribed_medicine_name || m.medicine_name }}</div>
                    <span :class="getMedicineStatusClass(m.status)" style="margin-left:auto;">{{ m.status }}</span>
                  </div>
                  <div class="prx-med-details">
                    <span class="prx-med-pill">{{ m.dosage }}</span>
                    <span class="prx-med-pill">{{ m.frequency }}</span>
                    <span class="prx-med-pill">{{ m.route }}</span>
                  </div>
                  <div v-if="m.instructions" class="prx-med-note">{{ m.instructions }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Prescriptions list */
.prx-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.prx-card {
  cursor: pointer;
  transition: transform 0.18s, box-shadow 0.18s;
}

.prx-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.10);
}

.prx-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
}

.prx-left {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.prx-icon {
  width: 40px;
  height: 40px;
  background: #f0fdfa;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.prx-doctor {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.prx-specialty {
  font-weight: 400;
  color: #64748b;
}

.prx-date, .prx-diagnosis {
  font-size: 12px;
  color: #64748b;
  margin-top: 3px;
}

.prx-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
  flex-shrink: 0;
}

.prx-followup {
  font-size: 11px;
  color: #64748b;
}

.prx-view-link {
  font-size: 11px;
  font-weight: 700;
  color: #0d9488;
}

/* Medicine grid */
.medicine-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 18px;
}

.med-card {
  transition: transform 0.18s, box-shadow 0.18s;
}

.med-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.10);
}

.med-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 14px;
}

.med-avatar {
  font-size: 22px;
  flex-shrink: 0;
}

.med-name {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.3;
}

.med-generic {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 2px;
}

.med-details {
  margin-bottom: 12px;
}

.dose-times {
  padding: 10px 0;
  border-top: 1px solid #f1f5f9;
  margin-bottom: 10px;
}

.dose-label {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #94a3b8;
  margin-bottom: 6px;
}

.dose-chips {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.dose-chip {
  padding: 3px 10px;
  background: #f0fdfa;
  border: 1px solid #99f6e4;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  color: #0f766e;
  font-variant-numeric: tabular-nums;
}

.med-instructions {
  font-size: 12px;
  color: #64748b;
  padding: 8px 12px;
  background: #fffbeb;
  border-radius: 8px;
  border: 1px solid #fde68a;
  margin-bottom: 10px;
}

.med-uses {
  padding-top: 10px;
  border-top: 1px solid #f1f5f9;
}

/* Detail Drawer */
.detail-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  backdrop-filter: blur(4px);
  z-index: 100;
  display: flex;
  justify-content: flex-end;
}

.detail-drawer {
  background: white;
  width: 540px;
  max-width: 95vw;
  height: 100%;
  overflow-y: auto;
  padding: 32px 28px;
  animation: slideIn 0.25s cubic-bezier(0.22, 1, 0.36, 1);
}

@keyframes slideIn {
  from { transform: translateX(100%); }
  to   { transform: translateX(0); }
}

.drawer-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
}

.drawer-title {
  font-size: 22px;
  font-weight: 800;
  color: #0f172a;
  margin: 6px 0 4px;
  letter-spacing: -0.5px;
}

.drawer-subtitle {
  font-size: 13px;
  color: #64748b;
}

.drawer-header-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
  flex-shrink: 0;
}

.drawer-section {
  margin-bottom: 24px;
}

.drawer-section-title {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 1.2px;
  text-transform: uppercase;
  color: #94a3b8;
  margin-bottom: 8px;
}

.drawer-text {
  font-size: 14px;
  color: #334155;
  line-height: 1.6;
  margin: 0;
  padding: 12px 16px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.followup-banner {
  padding: 12px 16px;
  background: #f0fdfa;
  border: 1px solid #99f6e4;
  border-radius: 8px;
  font-size: 13px;
  color: #0f766e;
  margin-bottom: 20px;
}

.prx-medicines {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.prx-medicine-card {
  padding: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fafcff;
}

.prx-med-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.prx-med-icon { font-size: 16px; }

.prx-med-name {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.prx-med-details {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}

.prx-med-pill {
  padding: 2px 9px;
  background: #f1f5f9;
  border-radius: 999px;
  font-size: 11px;
  color: #475569;
  font-weight: 600;
}

.prx-med-note {
  font-size: 12px;
  color: #64748b;
  font-style: italic;
}

.drawer-empty {
  padding: 24px;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
}
</style>
