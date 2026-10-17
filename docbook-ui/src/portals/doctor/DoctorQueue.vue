<script setup>
import { ref, onMounted, computed, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { call } from '../../api'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const queueData = ref(null)
const loading = ref(true)
const refreshing = ref(false)
const callingNext = ref(false)
const callError = ref(null)

let pollTimer = null

const nowServing = computed(() => {
  return queueData.value?.now_serving || null
})

const waitingList = computed(() => {
  const q = queueData.value?.queue || []
  return q.filter(r => r.visit_stage !== 'In Consultation')
})

const completedToday = computed(() => {
  const other = queueData.value?.other || []
  return other.filter(r => r.status === 'Completed' || r.visit_stage === 'Completed')
})

async function fetchQueue(isQuiet = false) {
  if (!isQuiet) loading.value = true
  else refreshing.value = true
  callError.value = null

  try {
    const res = await call('docbook.api.queue.get_queue', {})
    queueData.value = res
  } catch (err) {
    if (!isQuiet) {
      callError.value = err.message || 'Unable to load your live queue.'
    }
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

async function callNextPatient() {
  if (callingNext.value) return
  callingNext.value = true
  callError.value = null

  try {
    const res = await call('docbook.api.queue.call_next_patient', {})
    if (res?.called) {
      await fetchQueue(true)
      // First patient is automatically in consultation -> navigate to consultation form!
      router.push(`/consultation/${res.called}`)
      return
    }
    callError.value = res?.message || 'No patients are currently waiting in your queue.'
  } catch (err) {
    callError.value = err.message || 'Unable to call next patient.'
  } finally {
    callingNext.value = false
  }
}

async function callSpecificPatient(appt) {
  if (callingNext.value) return
  callingNext.value = true
  callError.value = null
  try {
    // If patient is not yet called, update stage to In Consultation
    await call('docbook.api.queue.call_next_patient', {
      doctor: appt.doctor,
    })
    router.push(`/consultation/${appt.name}`)
  } catch {
    // Direct navigate to consultation
    router.push(`/consultation/${appt.name}`)
  } finally {
    callingNext.value = false
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
  fetchQueue()
  pollTimer = setInterval(() => {
    fetchQueue(true)
  }, 15000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <main class="doc-queue-page">
    <div class="doc-shell">

      <!-- Header -->
      <header class="doc-header">
        <div>
          <div class="doc-eyebrow">
            <span>🩺</span>
            DOCTOR CLINICAL WORKSPACE
          </div>
          <h1>Live Patient Queue<span>.</span></h1>
          <p class="doc-sub">
            Call waiting patients into consultation, record clinical diagnosis, prescribe medicines, and request investigations.
          </p>
        </div>

        <div class="header-actions">
          <button
            class="btn-call-next"
            :disabled="callingNext || loading"
            @click="callNextPatient"
          >
            <span class="bell-icon">📣</span>
            {{ callingNext ? 'Calling Patient…' : 'Call Next Patient' }}
          </button>
          <button
            class="btn-refresh"
            :disabled="loading || refreshing"
            @click="fetchQueue(true)"
          >
            {{ refreshing ? 'Refreshing…' : '↻ Refresh' }}
          </button>
        </div>
      </header>

      <!-- Error banner -->
      <div v-if="callError" class="error-banner">
        <span>⚠️</span>
        <div class="flex-1">{{ callError }}</div>
        <button class="err-dismiss" @click="callError = null">✕</button>
      </div>

      <!-- Quick Metrics Strip -->
      <section class="queue-metrics">
        <div class="metric-card">
          <span class="m-label">Waiting in Queue</span>
          <strong class="m-val" style="color: #d97706;">{{ waitingList.length }}</strong>
          <span class="m-hint">Checked in &amp; ready</span>
        </div>
        <div class="metric-card">
          <span class="m-label">Now Serving</span>
          <strong class="m-val" style="color: #059669;">{{ nowServing ? '1 Patient' : 'Room Clear' }}</strong>
          <span class="m-hint">{{ nowServing ? nowServing.patient_name || nowServing.patient : 'Ready for next' }}</span>
        </div>
        <div class="metric-card">
          <span class="m-label">Completed Today</span>
          <strong class="m-val" style="color: #2563eb;">{{ completedToday.length }}</strong>
          <span class="m-hint">Consultations finished</span>
        </div>
      </section>

      <!-- CURRENTLY IN CONSULTATION HIGHLIGHT CARD -->
      <section v-if="nowServing" class="serving-card">
        <div class="serving-top">
          <div class="serving-badge">
            <span class="pulsing-dot">●</span>
            CURRENTLY IN CONSULTATION
          </div>
          <span class="serving-token">Token #{{ nowServing.queue_token }}</span>
        </div>

        <div class="serving-body">
          <div class="serving-avatar">
            {{ (nowServing.patient_name || nowServing.patient || 'P').charAt(0).toUpperCase() }}
          </div>
          <div class="serving-info">
            <h2>{{ nowServing.patient_name || nowServing.patient }}</h2>
            <div class="serving-meta">
              <span>Appointment #{{ nowServing.name }}</span>
              <span> · Scheduled: {{ formatTime(nowServing.appointment_time) }}</span>
              <span v-if="nowServing.called_at"> · Called at: {{ formatTime(nowServing.called_at) }}</span>
            </div>
            <div v-if="nowServing.reason" class="serving-complaint">
              <strong>Chief Complaint:</strong> {{ nowServing.reason }}
            </div>
            <div v-if="nowServing.symptoms" class="serving-symptoms">
              <strong>Symptoms:</strong> {{ nowServing.symptoms }}
            </div>
          </div>

          <button
            class="btn-open-consult"
            @click="router.push(`/consultation/${nowServing.name}`)"
          >
            ✏️ Open Consultation Form →
          </button>
        </div>
      </section>

      <!-- WAITING PATIENTS QUEUE TABLE -->
      <section class="queue-list-section">
        <div class="section-head">
          <h3>
            Patients Waiting in Room Queue ({{ waitingList.length }})
          </h3>
          <span class="queue-subhint">Sorted by arrival priority and token number</span>
        </div>

        <div v-if="loading && !waitingList.length" class="loading-box">
          <div class="spinner"></div>
          <p>Loading waiting queue…</p>
        </div>

        <div v-else-if="!waitingList.length" class="empty-queue-card">
          <div class="empty-icon">🛋️</div>
          <h3>Your Waiting Room is Clear</h3>
          <p>No patients are currently waiting for your consultation. Check today's schedule or receptionist check-ins.</p>
          <button class="btn-secondary" @click="router.push('/doctor-appointments')">
            View All Appointments
          </button>
        </div>

        <div v-else class="queue-table-card">
          <table class="q-table">
            <thead>
              <tr>
                <th>Queue Pos</th>
                <th>Token</th>
                <th>Patient Details</th>
                <th>Appointment Time</th>
                <th>Chief Complaint / Symptoms</th>
                <th>Priority</th>
                <th style="text-align: right;">Action</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(p, index) in waitingList"
                :key="p.name"
                :class="{ 'row-first': index === 0 }"
              >
                <!-- Pos -->
                <td>
                  <span class="pos-badge" :class="{ 'pos-badge--next': index === 0 }">
                    {{ index === 0 ? 'NEXT' : `#${index + 1}` }}
                  </span>
                </td>

                <!-- Token -->
                <td>
                  <strong class="token-val">#{{ p.queue_token }}</strong>
                </td>

                <!-- Patient -->
                <td>
                  <div class="patient-cell">
                    <div class="patient-name">{{ p.patient_name || p.patient }}</div>
                    <div class="patient-sub text-xs text-slate-500">
                      #{{ p.name }}
                      <span v-if="p.patient_phone"> · 📞 {{ p.patient_phone }}</span>
                    </div>
                  </div>
                </td>

                <!-- Time -->
                <td>
                  <strong>{{ formatTime(p.appointment_time) }}</strong>
                </td>

                <!-- Reason / Symptoms -->
                <td>
                  <div class="complaint-cell">
                    <div v-if="p.reason" class="c-reason">{{ p.reason }}</div>
                    <div v-if="p.symptoms" class="c-symptoms text-xs text-slate-500">
                      <strong>Symptoms:</strong> {{ p.symptoms }}
                    </div>
                    <div v-if="!p.reason && !p.symptoms" class="text-xs text-slate-400">Regular consultation</div>
                  </div>
                </td>

                <!-- Priority -->
                <td>
                  <span v-if="p.fast_track" class="tag-fast">⚡ Fast Track</span>
                  <span v-else-if="p.priority" class="tag-return">Priority Return</span>
                  <span v-else class="tag-normal">Normal</span>
                </td>

                <!-- Action -->
                <td style="text-align: right;">
                  <button
                    class="btn-call-row"
                    :disabled="callingNext"
                    @click="callSpecificPatient(p)"
                  >
                    {{ index === 0 ? '▶ Call Next' : 'Call In' }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

    </div>
  </main>
</template>

<style scoped>
.doc-queue-page {
  min-height: 100vh;
  background: #f8fafc;
  padding: 32px 24px;
  color: #0f172a;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
.doc-shell {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
}
.doc-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 16px;
}
.doc-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: #059669;
  text-transform: uppercase;
  margin-bottom: 4px;
}
.doc-header h1 {
  font-size: 32px;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
  letter-spacing: -0.02em;
}
.doc-header h1 span { color: #059669; }
.doc-sub { color: #64748b; font-size: 14px; margin: 6px 0 0; }

.header-actions { display: flex; gap: 10px; align-items: center; }
.btn-call-next {
  background: #059669;
  color: #ffffff;
  border: none;
  border-radius: 12px;
  padding: 12px 22px;
  font-size: 15px;
  font-weight: 800;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
  box-shadow: 0 4px 14px rgba(5,150,105,0.3);
}
.btn-call-next:hover { background: #047857; transform: translateY(-1px); }
.btn-call-next:disabled { opacity: 0.6; cursor: wait; }
.bell-icon { font-size: 18px; }

.btn-refresh {
  background: #ffffff;
  color: #334155;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  padding: 12px 18px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}
.btn-refresh:hover { background: #f1f5f9; }

/* Metrics */
.queue-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}
.metric-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.02);
}
.m-label { font-size: 12px; font-weight: 700; color: #64748b; text-transform: uppercase; }
.m-val { font-size: 30px; font-weight: 800; line-height: 1.1; margin: 4px 0; }
.m-hint { font-size: 12px; color: #94a3b8; }

/* Serving Card */
.serving-card {
  background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%);
  border: 2px solid #86efac;
  border-radius: 18px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: 0 4px 16px rgba(5,150,105,0.08);
}
.serving-top { display: flex; justify-content: space-between; align-items: center; }
.serving-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #dcfce7;
  color: #166534;
  font-size: 11px;
  font-weight: 800;
  padding: 4px 10px;
  border-radius: 20px;
  letter-spacing: 0.05em;
}
.pulsing-dot { color: #16a34a; animation: pulse-dot 1.2s infinite; }
@keyframes pulse-dot { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
.serving-token { font-size: 20px; font-weight: 900; color: #065f46; }

.serving-body {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}
.serving-avatar {
  width: 60px;
  height: 60px;
  border-radius: 16px;
  background: #059669;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  font-weight: 800;
  flex-shrink: 0;
}
.serving-info { flex: 1; min-width: 240px; }
.serving-info h2 { font-size: 22px; font-weight: 800; color: #0f172a; margin: 0 0 4px; }
.serving-meta { font-size: 13px; color: #64748b; margin-bottom: 8px; }
.serving-complaint, .serving-symptoms { font-size: 13px; color: #1e293b; line-height: 1.4; }

.btn-open-consult {
  background: #0f172a;
  color: #ffffff;
  border: none;
  border-radius: 12px;
  padding: 14px 24px;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.15s;
  box-shadow: 0 4px 12px rgba(15,23,42,0.15);
}
.btn-open-consult:hover { background: #1e293b; transform: translateY(-1px); }

/* Queue Table */
.queue-list-section { display: flex; flex-direction: column; gap: 12px; }
.section-head { display: flex; justify-content: space-between; align-items: baseline; }
.section-head h3 { font-size: 16px; font-weight: 800; color: #0f172a; margin: 0; }
.queue-subhint { font-size: 12px; color: #64748b; }

.queue-table-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 2px 10px rgba(0,0,0,0.02);
}
.q-table { width: 100%; border-collapse: collapse; font-size: 13px; text-align: left; }
.q-table th {
  background: #f8fafc;
  padding: 12px 16px;
  font-size: 11px;
  font-weight: 800;
  color: #64748b;
  text-transform: uppercase;
  border-bottom: 1px solid #e2e8f0;
}
.q-table td { padding: 14px 16px; border-bottom: 1px solid #f1f5f9; vertical-align: middle; }
.row-first { background: #fffdf5; }
.pos-badge {
  font-size: 11px;
  font-weight: 800;
  color: #64748b;
  background: #f1f5f9;
  padding: 4px 8px;
  border-radius: 6px;
}
.pos-badge--next { background: #fef3c7; color: #b45309; }
.token-val { font-size: 15px; color: #0f172a; }

.patient-name { font-weight: 700; color: #0f172a; font-size: 14px; }
.complaint-cell { max-width: 280px; font-size: 12px; }
.c-reason { font-weight: 600; color: #1e293b; }

.tag-fast { background: #fee2e2; color: #b91c1c; font-size: 10px; font-weight: 800; padding: 2px 6px; border-radius: 4px; }
.tag-return { background: #ede9fe; color: #6b21a8; font-size: 10px; font-weight: 800; padding: 2px 6px; border-radius: 4px; }
.tag-normal { background: #f1f5f9; color: #64748b; font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 4px; }

.btn-call-row {
  background: #059669;
  color: #ffffff;
  border: none;
  border-radius: 8px;
  padding: 7px 16px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s;
}
.btn-call-row:hover { background: #047857; }

.empty-queue-card {
  background: #ffffff;
  border: 1px dashed #cbd5e1;
  border-radius: 16px;
  padding: 48px 24px;
  text-align: center;
}
.empty-icon { font-size: 40px; margin-bottom: 10px; }
.empty-queue-card h3 { font-size: 18px; font-weight: 800; color: #0f172a; margin: 0 0 6px; }
.empty-queue-card p { color: #64748b; font-size: 14px; margin: 0 0 16px; }
.btn-secondary {
  background: #ffffff;
  color: #334155;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 10px 18px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.error-banner {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
  border-radius: 12px;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
}
.err-dismiss { background: none; border: none; color: #991b1b; cursor: pointer; }
.loading-box { text-align: center; padding: 48px; color: #64748b; }
.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid #e2e8f0;
  border-top-color: #059669;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 10px;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
