<script setup>
import { ref, onMounted } from 'vue'
import { call } from '../../api'

const referrals = ref([])
const loading = ref(true)
const error = ref(null)
const busy = ref(false)

// Detail drawer
const selected = ref(null)
const detail = ref(null)
const detailLoading = ref(false)
const detailError = ref(null)

async function fetchReferrals() {
  loading.value = true
  error.value = null
  try {
    const res = await call('docbook.api.referral.list_my_referrals')
    referrals.value = Array.isArray(res) ? res : []
  } catch (e) {
    error.value = e.message || 'Unable to load referrals.'
  } finally {
    loading.value = false
  }
}

async function openDetail(r) {
  selected.value = r
  detail.value = null
  detailError.value = null
  detailLoading.value = true
  try {
    detail.value = await call('docbook.api.referral.get_referral', { referral: r.name })
  } catch (e) {
    detailError.value = e.message || 'Failed to load referral.'
  } finally {
    detailLoading.value = false
  }
}

function closeDetail() {
  selected.value = null
  detail.value = null
}

async function accept(r) {
  busy.value = true
  try {
    await call('docbook.api.referral.accept_referral', { referral: r.name })
    await fetchReferrals()
    if (selected.value?.name === r.name) await openDetail(r)
  } catch (e) {
    error.value = e.message || 'Unable to accept.'
  } finally {
    busy.value = false
  }
}

async function complete(r) {
  busy.value = true
  try {
    await call('docbook.api.referral.complete_referral', { referral: r.name })
    await fetchReferrals()
    if (selected.value?.name === r.name) await openDetail(r)
  } catch (e) {
    error.value = e.message || 'Unable to complete.'
  } finally {
    busy.value = false
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

onMounted(fetchReferrals)
</script>

<template>
  <div class="db-page">
    <div class="db-container">
      <header style="margin-bottom: 28px;">
        <div class="db-eyebrow">DOCTOR PORTAL</div>
        <h1 class="db-page-title">Referrals</h1>
        <p class="db-section-subtitle">Specialist referrals you made or received, with shared reports and notes.</p>
      </header>

      <div v-if="error" class="db-error-panel">
        <span>⚠️</span><span>{{ error }}</span>
        <button class="db-btn db-btn--secondary" style="margin-left:auto" @click="fetchReferrals">Retry</button>
      </div>

      <div v-if="loading" class="ref-grid">
        <div v-for="i in 3" :key="i" class="db-card" style="min-height:110px"></div>
      </div>

      <div v-else-if="referrals.length === 0" class="db-empty">
        <div class="db-empty-icon">🤝</div>
        <h3>No referrals yet</h3>
        <p>Referrals you create during a consultation, or that are sent to you, will show here.</p>
      </div>

      <div v-else class="ref-grid">
        <article v-for="r in referrals" :key="r.name" class="db-card ref-card">
          <div class="ref-top">
            <span class="ref-id">{{ r.name }}</span>
            <span :class="statusClass(r.status)">{{ r.status }}</span>
          </div>
          <h3 class="ref-patient">{{ r.patient_name || r.patient }}</h3>
          <p class="ref-line">➡ {{ r.specialty || 'Specialist' }} · {{ r.role || (r.referring_doctor === r.referred_to_doctor ? '' : '') }}</p>
          <p class="ref-reason">{{ r.reason }}</p>
          <div class="ref-meta">
            <span>{{ formatDate(r.referral_date) }}</span>
            <span>📎 {{ r.report_count || 0 }} reports</span>
          </div>
          <div class="ref-actions">
            <button class="db-btn db-btn--secondary" @click="openDetail(r)">View</button>
            <button v-if="r.status === 'Pending' && r.role !== 'Referring'" class="db-btn db-btn--primary" :disabled="busy" @click="accept(r)">Accept</button>
            <button v-if="r.status === 'Accepted'" class="db-btn db-btn--ghost" :disabled="busy" @click="complete(r)">Complete</button>
          </div>
        </article>
      </div>

      <!-- Detail drawer -->
      <div v-if="selected" class="ref-overlay" @click.self="closeDetail">
        <div class="ref-drawer">
          <div class="ref-drawer-head">
            <div>
              <span class="ref-id">{{ selected.name }}</span>
              <h2>{{ selected.patient_name || selected.patient }}</h2>
            </div>
            <button class="ref-close" @click="closeDetail">✕</button>
          </div>

          <div v-if="detailLoading" class="db-empty"><div class="db-empty-icon">⏳</div><p>Loading…</p></div>
          <div v-else-if="detailError" class="db-error-panel">{{ detailError }}</div>

          <template v-else-if="detail">
            <div class="ref-sec">
              <h4>Reason</h4>
              <p class="ref-block">{{ detail.reason }}</p>
              <div class="ref-badges">
                <span :class="statusClass(detail.status)">{{ detail.status }}</span>
                <span class="ref-chip">{{ detail.specialty }}</span>
              </div>
            </div>

            <div class="ref-sec">
              <h4>Appointments (shared episode)</h4>
              <div v-for="a in detail.appointments" :key="a.name" class="ref-appt">
                <div>
                  <p class="ref-appt-name">{{ a.name }}</p>
                  <p class="ref-appt-sub">{{ a.appointment_date }} · {{ a.appointment_time }} · {{ a.doctor }}</p>
                </div>
                <span class="db-badge db-badge--confirmed">{{ a.status }}</span>
              </div>
            </div>

            <div class="ref-sec">
              <h4>Shared reports</h4>
              <div v-if="!detail.reports || detail.reports.length === 0" class="ref-none">No reports yet.</div>
              <div v-for="rp in detail.reports" :key="rp.name" class="ref-report">
                <div>
                  <p class="ref-appt-name">{{ rp.title }}</p>
                  <p class="ref-appt-sub">{{ rp.report_type }} · {{ rp.laboratory || '—' }}</p>
                </div>
                <span :class="statusClass(rp.status)">{{ rp.status }}</span>
                <a v-if="rp.report_file" :href="rp.report_file" target="_blank" class="ref-open">Open ↗</a>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ref-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }
.ref-card { display: flex; flex-direction: column; gap: 8px; }
.ref-top { display: flex; justify-content: space-between; align-items: center; }
.ref-id { font-size: 12px; font-weight: 800; color: #0d9488; letter-spacing: 0.4px; }
.ref-patient { margin: 0; font-size: 17px; font-weight: 800; color: #0f172a; }
.ref-line { margin: 0; font-size: 13px; font-weight: 600; color: #475569; }
.ref-reason { margin: 0; font-size: 13px; color: #64748b; }
.ref-meta { display: flex; justify-content: space-between; font-size: 12px; color: #94a3b8; }
.ref-actions { display: flex; gap: 8px; margin-top: 6px; }

.ref-overlay { position: fixed; inset: 0; background: rgba(15,23,42,0.4); backdrop-filter: blur(4px); z-index: 1000; display: flex; justify-content: flex-end; }
.ref-drawer { background: #fff; width: 520px; max-width: 95vw; height: 100%; overflow-y: auto; padding: 28px 26px; animation: refIn 0.25s cubic-bezier(0.22,0.36,1); }
@keyframes refIn { from { transform: translateX(100%); } to { transform: translateX(0); } }
.ref-drawer-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 22px; }
.ref-drawer-head h2 { margin: 4px 0 0; font-size: 22px; font-weight: 800; color: #0f172a; }
.ref-close { background: none; border: none; font-size: 18px; color: #94a3b8; cursor: pointer; }
.ref-sec { margin-bottom: 24px; }
.ref-sec h4 { font-size: 10px; font-weight: 800; letter-spacing: 1.1px; text-transform: uppercase; color: #94a3b8; margin: 0 0 8px; }
.ref-block { font-size: 14px; color: #334155; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 14px; margin: 0; }
.ref-badges { display: flex; gap: 8px; margin-top: 10px; }
.ref-chip { font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 999px; background: #f0fdfa; color: #0f766e; border: 1px solid #99f6e4; }
.ref-appt, .ref-report { display: flex; align-items: center; gap: 12px; padding: 12px 14px; border: 1px solid #e2e8f0; border-radius: 10px; margin-bottom: 8px; }
.ref-appt-name { margin: 0; font-size: 14px; font-weight: 700; color: #0f172a; }
.ref-appt-sub { margin: 2px 0 0; font-size: 12px; color: #64748b; }
.ref-report > div { flex: 1; }
.ref-open { font-size: 13px; font-weight: 700; color: #0d9488; text-decoration: none; }
.ref-none { font-size: 13px; color: #94a3b8; }
</style>


