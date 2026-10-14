<script setup>
import { ref, onMounted } from 'vue'
import { call, uploadFile } from '../../api'

const reports = ref([])
const loading = ref(true)
const error = ref(null)
const busy = ref(false)

const showUpload = ref(false)
const uploading = ref(false)
const uploadError = ref(null)
const activeReport = ref(null)
const form = ref({ findings: '', laboratory: '', file: null })

async function fetchWorklist() {
  loading.value = true
  error.value = null
  try {
    const res = await call('docbook.api.report.list_pending_reports')
    reports.value = Array.isArray(res) ? res : []
  } catch (e) {
    error.value = e.message || 'Unable to load worklist.'
  } finally {
    loading.value = false
  }
}

async function collect(r) {
  busy.value = true
  try {
    await call('docbook.api.report.mark_sample_collected', { report: r.name })
    await fetchWorklist()
  } catch (e) {
    error.value = e.message || 'Unable to update.'
  } finally {
    busy.value = false
  }
}

function openUpload(r) {
  activeReport.value = r
  uploadError.value = null
  form.value = { findings: '', laboratory: r.laboratory || '', file: null }
  showUpload.value = true
}

function onFileChange(e) {
  form.value.file = e.target.files?.[0] || null
}

async function submitUpload() {
  uploadError.value = null
  const f = form.value
  if (!f.file && !f.findings?.trim()) {
    uploadError.value = 'Attach a file or enter findings.'
    return
  }
  uploading.value = true
  try {
    let fileUrl = ''
    if (f.file) fileUrl = (await uploadFile(f.file)) || ''
    await call('docbook.api.report.upload_report', {
      report: activeReport.value.name,
      file_url: fileUrl,
      findings: f.findings || '',
      laboratory: f.laboratory || '',
    })
    showUpload.value = false
    await fetchWorklist()
  } catch (e) {
    uploadError.value = e.message || 'Upload failed.'
  } finally {
    uploading.value = false
  }
}

function statusClass(s) {
  return `db-badge db-badge--${(s || 'pending').toLowerCase()}`
}

onMounted(fetchWorklist)
</script>

<template>
  <div class="db-page">
    <div class="db-container">
      <header style="margin-bottom: 28px;">
        <div class="db-eyebrow">LABORATORY PORTAL</div>
        <h1 class="db-page-title">Lab Worklist</h1>
        <p class="db-section-subtitle">Ordered and in-progress tests awaiting result upload.</p>
      </header>

      <div v-if="error" class="db-error-panel">
        <span>⚠️</span><span>{{ error }}</span>
        <button class="db-btn db-btn--secondary" style="margin-left:auto" @click="fetchWorklist">Retry</button>
      </div>

      <div v-if="loading" class="lab-grid">
        <div v-for="i in 3" :key="i" class="db-card" style="min-height:100px"></div>
      </div>

      <div v-else-if="reports.length === 0" class="db-empty">
        <div class="db-empty-icon">🧪</div>
        <h3>No pending tests</h3>
        <p>Reports ordered by doctors will appear here for processing.</p>
      </div>

      <div v-else class="lab-grid">
        <article v-for="r in reports" :key="r.name" class="db-card lab-card">
          <div class="lab-top">
            <span class="lab-type">{{ r.report_type }}</span>
            <span :class="statusClass(r.status)">{{ r.status }}</span>
          </div>
          <h3 class="lab-title">{{ r.title }}</h3>
          <p class="lab-sub">Patient: {{ r.patient }}</p>
          <p class="lab-sub">Appointment: {{ r.appointment || '—' }}</p>
          <p v-if="r.description" class="lab-desc">{{ r.description }}</p>
          <div class="lab-actions">
            <button v-if="r.status === 'Ordered'" class="db-btn db-btn--secondary" :disabled="busy" @click="collect(r)">Mark sample</button>
            <button class="db-btn db-btn--primary" @click="openUpload(r)">⬆ Upload result</button>
          </div>
        </article>
      </div>

      <div v-if="showUpload" class="lab-overlay" @click.self="showUpload = false">
        <div class="lab-modal">
          <div class="lab-modal-head">
            <h3>Upload result — {{ activeReport?.title }}</h3>
            <button class="lab-close" @click="showUpload = false">✕</button>
          </div>
          <div class="lab-modal-body">
            <div v-if="uploadError" class="lab-error">{{ uploadError }}</div>
            <label class="lab-label">Laboratory</label>
            <input v-model="form.laboratory" class="lab-input" placeholder="e.g. Metropolis" />
            <label class="lab-label">Result file</label>
            <input type="file" class="lab-input" @change="onFileChange" />
            <label class="lab-label">Findings</label>
            <textarea v-model="form.findings" class="lab-input" rows="4" placeholder="Key values, reference ranges…"></textarea>
          </div>
          <div class="lab-modal-foot">
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
.lab-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }
.lab-card { display: flex; flex-direction: column; gap: 6px; }
.lab-top { display: flex; justify-content: space-between; align-items: center; }
.lab-type { font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.6px; color: #0d9488; }
.lab-title { margin: 0; font-size: 16px; font-weight: 800; color: #0f172a; }
.lab-sub { margin: 0; font-size: 12px; color: #64748b; }
.lab-desc { margin: 4px 0 0; font-size: 13px; color: #334155; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 10px; }
.lab-actions { display: flex; gap: 8px; margin-top: 8px; }

.lab-overlay { position: fixed; inset: 0; background: rgba(15,23,42,0.4); backdrop-filter: blur(3px); z-index: 1000; display: flex; align-items: center; justify-content: center; padding: 20px; }
.lab-modal { background: #fff; border-radius: 16px; width: 100%; max-width: 440px; max-height: 88vh; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 24px 64px rgba(15,23,42,0.2); }
.lab-modal-head { display: flex; justify-content: space-between; align-items: center; padding: 18px 20px; border-bottom: 1px solid #f1f5f9; }
.lab-modal-head h3 { margin: 0; font-size: 15px; font-weight: 800; color: #0f172a; }
.lab-close { background: none; border: none; font-size: 16px; color: #94a3b8; cursor: pointer; }
.lab-modal-body { padding: 18px 20px; overflow-y: auto; }
.lab-modal-foot { display: flex; justify-content: flex-end; gap: 10px; padding: 14px 20px; border-top: 1px solid #f1f5f9; }
.lab-label { display: block; font-size: 12px; font-weight: 700; color: #475569; margin: 12px 0 6px; }
.lab-input { width: 100%; padding: 9px 11px; border: 1px solid #e2e8f0; border-radius: 9px; font-size: 13px; color: #0f172a; outline: none; font-family: inherit; box-sizing: border-box; }
.lab-input:focus { border-color: #0d9488; box-shadow: 0 0 0 3px rgba(13,148,136,0.12); }
.lab-error { background: #fef2f2; border: 1px solid #fecaca; color: #b91c1c; font-size: 12px; padding: 10px 12px; border-radius: 9px; margin-bottom: 8px; }
</style>

