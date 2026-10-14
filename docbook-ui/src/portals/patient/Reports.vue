<script setup>
import { ref, onMounted } from 'vue'
import { call, uploadFile } from '../../api'

const reports = ref([])
const appointments = ref([])
const loading = ref(true)
const error = ref(null)

const showUpload = ref(false)
const uploading = ref(false)
const uploadError = ref(null)
const form = ref({ appointment: '', report_type: 'Lab', title: '', laboratory: '', findings: '', file: null })

async function fetchReports() {
  loading.value = true
  error.value = null
  try {
    const res = await call('docbook.api.report.list_reports')
    reports.value = Array.isArray(res) ? res : []
  } catch (e) {
    error.value = e.message || 'Unable to load reports.'
  } finally {
    loading.value = false
  }
}

async function openUpload() {
  uploadError.value = null
  form.value = { appointment: '', report_type: 'Lab', title: '', laboratory: '', findings: '', file: null }
  try {
    const res = await call('docbook.api.appointment.list_appointment')
    appointments.value = (Array.isArray(res) ? res : []).filter((a) => a.status !== 'Cancelled')
  } catch (e) {
    appointments.value = []
  }
  showUpload.value = true
}

function onFileChange(e) {
  form.value.file = e.target.files?.[0] || null
}

async function submitUpload() {
  uploadError.value = null
  const f = form.value
  if (!f.appointment || !f.title?.trim()) {
    uploadError.value = 'Please choose an appointment and enter a title.'
    return
  }
  if (!f.file && !f.findings?.trim()) {
    uploadError.value = 'Attach a file or enter findings.'
    return
  }
  uploading.value = true
  try {
    let fileUrl = ''
    if (f.file) {
      fileUrl = (await uploadFile(f.file, { doctype: 'Appointment', docname: f.appointment })) || ''
    }
    await call('docbook.api.report.upload_external_report', {
      appointment: f.appointment,
      file_url: fileUrl,
      report_type: f.report_type,
      title: f.title,
      findings: f.findings || '',
      laboratory: f.laboratory || '',
    })
    showUpload.value = false
    await fetchReports()
  } catch (e) {
    uploadError.value = e.message || 'Upload failed.'
  } finally {
    uploading.value = false
  }
}

function formatDate(d) {
  if (!d) return '—'
  const dt = new Date(d)
  if (isNaN(dt)) return d
  return dt.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

function statusClass(s) {
  return `db-badge db-badge--${(s || 'pending').toLowerCase()}`
}

onMounted(fetchReports)
</script>

<template>
  <div class="db-page">
    <div class="db-container">
      <header class="rpt-header">
        <div>
          <div class="db-eyebrow">PATIENT PORTAL</div>
          <h1 class="db-page-title">My Reports</h1>
          <p class="db-section-subtitle">Lab, imaging and diagnostic reports for your visits.</p>
        </div>
        <button class="db-btn db-btn--primary" @click="openUpload">⬆ Upload Report</button>
      </header>

      <div v-if="error" class="db-error-panel">
        <span>⚠️</span><span>{{ error }}</span>
        <button class="db-btn db-btn--secondary" style="margin-left:auto" @click="fetchReports">Retry</button>
      </div>

      <div v-if="loading" class="rpt-grid">
        <div v-for="i in 3" :key="i" class="db-card" style="min-height:120px"></div>
      </div>

      <div v-else-if="reports.length === 0" class="db-empty">
        <div class="db-empty-icon">📄</div>
        <h3>No reports yet</h3>
        <p>Reports ordered by your doctors, or ones you upload, will appear here.</p>
      </div>

      <div v-else class="rpt-grid">
        <article v-for="r in reports" :key="r.name" class="db-card rpt-card">
          <div class="rpt-top">
            <span class="rpt-type">{{ r.report_type }}</span>
            <span :class="statusClass(r.status)">{{ r.status }}</span>
          </div>
          <h3 class="rpt-title">{{ r.title }}</h3>
          <div class="rpt-meta">
            <span v-if="r.laboratory">🏢 {{ r.laboratory }}</span>
            <span>🗓 {{ formatDate(r.uploaded_at || r.creation) }}</span>
            <span v-if="r.external" class="rpt-ext">External</span>
          </div>
          <p v-if="r.findings" class="rpt-findings">{{ r.findings }}</p>
          <a v-if="r.report_file" :href="r.report_file" target="_blank" class="rpt-link">Open report file ↗</a>
        </article>
      </div>

      <div v-if="showUpload" class="rpt-overlay" @click.self="showUpload = false">
        <div class="rpt-modal">
          <div class="rpt-modal-head">
            <h3>Upload an outside report</h3>
            <button class="rpt-close" @click="showUpload = false">✕</button>
          </div>
          <div class="rpt-modal-body">
            <div v-if="uploadError" class="rpt-error">{{ uploadError }}</div>
            <label class="rpt-label">Appointment</label>
            <select v-model="form.appointment" class="rpt-input">
              <option value="" disabled>Select appointment</option>
              <option v-for="a in appointments" :key="a.name" :value="a.name">
                {{ a.name }} — {{ a.doctor_name || a.doctor }} · {{ a.appointment_date }}
              </option>
            </select>

            <label class="rpt-label">Report type</label>
            <select v-model="form.report_type" class="rpt-input">
              <option>Lab</option><option>Imaging</option><option>Prescription</option>
              <option>Document</option><option>Other</option>
            </select>

            <label class="rpt-label">Title</label>
            <input v-model="form.title" class="rpt-input" placeholder="e.g. CBC Blood Test" />

            <label class="rpt-label">Laboratory / Provider (optional)</label>
            <input v-model="form.laboratory" class="rpt-input" placeholder="e.g. Metropolis" />

            <label class="rpt-label">File</label>
            <input type="file" class="rpt-input" @change="onFileChange" />

            <label class="rpt-label">Findings / notes (optional)</label>
            <textarea v-model="form.findings" class="rpt-input" rows="3" placeholder="Key values or notes"></textarea>
          </div>
          <div class="rpt-modal-foot">
            <button class="db-btn db-btn--secondary" @click="showUpload = false">Cancel</button>
            <button class="db-btn db-btn--primary" :disabled="uploading" @click="submitUpload">
              {{ uploading ? 'Uploading…' : 'Upload' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.rpt-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 28px; }
.rpt-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.rpt-card { display: flex; flex-direction: column; gap: 8px; }
.rpt-top { display: flex; justify-content: space-between; align-items: center; }
.rpt-type { font-size: 11px; font-weight: 800; letter-spacing: 0.6px; text-transform: uppercase; color: #0d9488; }
.rpt-title { font-size: 16px; font-weight: 800; color: #0f172a; margin: 0; }
.rpt-meta { display: flex; flex-wrap: wrap; gap: 10px; font-size: 12px; color: #64748b; }
.rpt-ext { background: #fef3c7; color: #92400e; padding: 1px 8px; border-radius: 999px; font-weight: 700; }
.rpt-findings { font-size: 13px; color: #334155; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 10px; margin: 0; }
.rpt-link { font-size: 13px; font-weight: 700; color: #0d9488; text-decoration: none; }
.rpt-link:hover { text-decoration: underline; }

.rpt-overlay { position: fixed; inset: 0; background: rgba(15,23,42,0.4); backdrop-filter: blur(3px); z-index: 1000; display: flex; align-items: center; justify-content: center; padding: 20px; }
.rpt-modal { background: #fff; border-radius: 16px; width: 100%; max-width: 460px; max-height: 88vh; display: flex; flex-direction: column; box-shadow: 0 24px 64px rgba(15,23,42,0.2); overflow: hidden; }
.rpt-modal-head { display: flex; justify-content: space-between; align-items: center; padding: 18px 20px; border-bottom: 1px solid #f1f5f9; }
.rpt-modal-head h3 { margin: 0; font-size: 16px; font-weight: 800; color: #0f172a; }
.rpt-close { background: none; border: none; font-size: 16px; color: #94a3b8; cursor: pointer; }
.rpt-modal-body { padding: 18px 20px; overflow-y: auto; }
.rpt-modal-foot { display: flex; justify-content: flex-end; gap: 10px; padding: 14px 20px; border-top: 1px solid #f1f5f9; }
.rpt-label { display: block; font-size: 12px; font-weight: 700; color: #475569; margin: 12px 0 6px; }
.rpt-input { width: 100%; padding: 9px 11px; border: 1px solid #e2e8f0; border-radius: 9px; font-size: 13px; color: #0f172a; outline: none; font-family: inherit; box-sizing: border-box; }
.rpt-input:focus { border-color: #0d9488; box-shadow: 0 0 0 3px rgba(13,148,136,0.12); }
.rpt-error { background: #fef2f2; border: 1px solid #fecaca; color: #b91c1c; font-size: 12px; padding: 10px 12px; border-radius: 9px; margin-bottom: 8px; }
@media (max-width: 640px) { .rpt-header { flex-direction: column; } }
</style>


