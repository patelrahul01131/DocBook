<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button, Dialog } from 'frappe-ui'
import { call } from '../../api'

const route = useRoute()
const router = useRouter()

const appointment = ref(null)
const loading = ref(true)
const error = ref(null)

// Reschedule Modal
const showRescheduleModal = ref(false)
const rescheduleDate = ref('')
const rescheduleTime = ref('')
const rescheduleReason = ref('')
const availableSlots = ref([])
const loadingSlots = ref(false)
const rescheduling = ref(false)
const rescheduleError = ref(null)

// Action states
const cancelling = ref(false)
const deleting = ref(false)

// QR pass + queue status
const showQrModal = ref(false)
const qrLoading = ref(false)
const qrError = ref(null)
const qrImgBroken = ref(false)
const queueInfo = ref(null)
let queuePoll = null

// AI consultation summary (completed appointments only)
const showAiSummaryModal = ref(false)
const aiSummaryLoading = ref(false)
const aiSummaryError = ref(null)
const aiSummary = ref(null)

async function fetchAppointment() {
  loading.value = true
  error.value = null

  try {
    const res = await call('docbook.api.appointment.show_appointment', {
      appointment_id: route.params.id,
    })
    // Support object response or legacy single-element list
    appointment.value = Array.isArray(res) ? res[0] : res
    if (appointment.value) {
      rescheduleDate.value = appointment.value.appointment_date || ''
      rescheduleTime.value = appointment.value.appointment_time || ''
      rescheduleReason.value = appointment.value.reason || ''
      loadQr()
      loadQueueInfo()
    }
  } catch (err) {
    console.error('Fetch appointment error:', err)
    error.value = err.message || 'Unable to load appointment details.'
  } finally {
    loading.value = false
  }
}

async function fetchAvailableSlots() {
  if (!rescheduleDate.value || !appointment.value?.doctor) return
  loadingSlots.value = true
  rescheduleError.value = null
  try {
    const slots = await call('docbook.api.appointment.get_available_slots', {
      doctor: appointment.value.doctor,
      date: rescheduleDate.value,
    })
    availableSlots.value = Array.isArray(slots) ? slots : []
  } catch (err) {
    availableSlots.value = []
    rescheduleError.value = err.message || 'Unable to load available slots.'
  } finally {
    loadingSlots.value = false
  }
}

function openReschedule() {
  if (!appointment.value) return
  rescheduleDate.value = appointment.value.appointment_date || ''
  rescheduleTime.value = appointment.value.appointment_time || ''
  rescheduleReason.value = appointment.value.reason || ''
  showRescheduleModal.value = true
  fetchAvailableSlots()
}

async function submitReschedule() {
  if (!rescheduleDate.value || !rescheduleTime.value) {
    rescheduleError.value = 'Please select both date and time slot.'
    return
  }
  rescheduling.value = true
  rescheduleError.value = null

  try {
    await call('docbook.api.appointment.update_appointment', {
      appointment_id: appointment.value.name,
      appointment_date: rescheduleDate.value,
      appointment_time: rescheduleTime.value,
      reason: rescheduleReason.value,
    })
    showRescheduleModal.value = false
    await fetchAppointment()
  } catch (err) {
    rescheduleError.value = err.message || 'Failed to reschedule appointment.'
  } finally {
    rescheduling.value = false
  }
}

async function cancelAppointment() {
  if (!confirm('Are you sure you want to cancel this appointment?')) return
  cancelling.value = true
  try {
    await call('docbook.api.appointment.cancel_appointment', {
      appointment_id: appointment.value.name,
      reason: 'Cancelled by patient',
    })
    await fetchAppointment()
  } catch (err) {
    alert(err.message || 'Failed to cancel appointment.')
  } finally {
    cancelling.value = false
  }
}

async function deleteAppointment() {
  if (!confirm('Are you sure you want to permanently delete this appointment record? This action cannot be undone.')) return
  deleting.value = true
  try {
    await call('docbook.api.appointment.delete_appointment', {
      appointment_id: appointment.value.name,
    })
    router.replace('/my-appointments')
  } catch (err) {
    alert(err.message || 'Failed to delete appointment.')
    deleting.value = false
  }
}

async function loadQr(force = false) {
  if (!appointment.value) return
  if (['Completed', 'Cancelled'].includes(appointment.value.status)) return
  if ((appointment.value.qr_data_url || appointment.value.qr_code) && !force) return
  qrLoading.value = true
  qrError.value = null
  qrImgBroken.value = false
  try {
    const res = await call('docbook.api.appointment.generate_qr_code', {
      appointment_id: appointment.value.name,
    })
    appointment.value.qr_code = res?.qr_code || null
    appointment.value.qr_data_url = res?.qr_data_url || null
  } catch (err) {
    qrError.value = err.message || 'Unable to generate QR code.'
  } finally {
    qrLoading.value = false
  }
}

function openQr() {
  showQrModal.value = true
  loadQr()
}

function retryQrImage() {
  qrImgBroken.value = false
  loadQr(true)
}

async function downloadQr() {
  if (!appointment.value) return
  if (!appointment.value.qr_data_url && !appointment.value.qr_code) {
    await loadQr(true)
  }
  const dataUrl = appointment.value.qr_data_url
  if (dataUrl && dataUrl.startsWith('data:image/')) {
    const link = document.createElement('a')
    link.href = dataUrl
    link.download = `QR-${appointment.value.name}.png`
    document.body.appendChild(link)
    link.click()
    link.remove()
    return
  }

  // Draw from img element onto canvas to ensure a clean local PNG download
  const qrImg = document.querySelector('.qr-img')
  if (qrImg && qrImg.naturalWidth) {
    try {
      const canvas = document.createElement('canvas')
      canvas.width = qrImg.naturalWidth
      canvas.height = qrImg.naturalHeight
      const ctx = canvas.getContext('2d')
      ctx.drawImage(qrImg, 0, 0)
      const pngUrl = canvas.toDataURL('image/png')
      const link = document.createElement('a')
      link.href = pngUrl
      link.download = `QR-${appointment.value.name}.png`
      document.body.appendChild(link)
      link.click()
      link.remove()
      return
    } catch (e) {
      console.warn('Canvas export failed, falling back to fetch', e)
    }
  }

  const url = appointment.value.qr_code
  if (!url) {
    alert(qrError.value || 'QR code is not available yet.')
    return
  }
  try {
    const resp = await fetch(url)
    const blob = await resp.blob()
    const link = document.createElement('a')
    const objectUrl = URL.createObjectURL(blob)
    link.href = objectUrl
    link.download = `QR-${appointment.value.name}.png`
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(objectUrl)
  } catch {
    window.open(url, '_blank')
  }
}

async function openAiSummary() {
  if (!appointment.value) return
  showAiSummaryModal.value = true
  aiSummaryLoading.value = true
  aiSummaryError.value = null
  aiSummary.value = null
  try {
    aiSummary.value = await call('docbook.api.prescription.ai_generate_summary', {
      appointment: appointment.value.name,
    })
    if (!aiSummary.value?.summary && !aiSummary.value?.key_points?.length) {
      aiSummaryError.value = 'AI could not generate a summary right now. Please try again.'
    }
  } catch (err) {
    aiSummaryError.value = err.message || 'AI summary failed. Please try again.'
  } finally {
    aiSummaryLoading.value = false
  }
}

async function loadQueueInfo() {
  if (!appointment.value) return
  if (['Completed', 'Cancelled'].includes(appointment.value.status)) {
    queueInfo.value = null
    return
  }
  try {
    queueInfo.value = await call('docbook.api.queue.get_my_queue_position', {
      appointment: appointment.value.name,
    })
  } catch {
    queueInfo.value = null
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
  if (!name) return 'DR'
  return name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()
}

const canEditOrCancel = computed(() => {
  return appointment.value && !['Completed', 'Cancelled'].includes(appointment.value.status)
})

onMounted(() => {
  fetchAppointment()
  // Keep queue/check-in status fresh while the appointment is active.
  queuePoll = setInterval(() => {
    if (appointment.value && !['Completed', 'Cancelled'].includes(appointment.value.status)) {
      loadQueueInfo()
    }
  }, 30000)
})

onUnmounted(() => {
  if (queuePoll) clearInterval(queuePoll)
})
</script>

<template>
  <div class="appointment-page">
    <div class="page-container">

      <!-- Loading -->
      <div v-if="loading" class="state-card">
        <div class="loader"></div>
        <p>Loading appointment details...</p>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="state-card error-card">
        <div class="error-icon">!</div>
        <div>
          <h2>Unable to load appointment</h2>
          <p>{{ error }}</p>
          <button class="retry-btn mt-3" @click="fetchAppointment">Try Again</button>
        </div>
      </div>

      <!-- Appointment Detail -->
      <div v-else-if="appointment" class="appointment-container">

        <!-- Top Header & Actions -->
        <header class="page-header">
          <div>
            <button class="back-link" @click="$router.back()">
              ← Back to Appointments
            </button>
            <div class="eyebrow">
              <span class="lucide-calendar"></span>
              APPOINTMENT RECORD
            </div>
            <h1>
              Appointment <span>#{{ appointment.name || appointment.slot }}</span>
            </h1>
            <p v-if="appointment.created_at" class="created-text">
              Booked on {{ formatDate(appointment.created_at.slice(0, 10)) }}
            </p>
          </div>

          <div class="header-right">
            <!-- Status Badge -->
            <span
              class="status-pill"
              :class="`status-${(appointment.status || 'pending').toLowerCase()}`"
            >
              {{ appointment.status }}
            </span>

            <!-- Priority / fast-track badges -->
            <span v-if="appointment.fast_track" class="priority-pill priority-pill--fast">⚡ Fast Track</span>
            <span v-else-if="appointment.priority" class="priority-pill priority-pill--return">Priority Return</span>
            <span v-if="appointment.ai_priority === 'High'" class="priority-pill priority-pill--high">AI: High Priority</span>

            <button
              v-if="!['Completed', 'Cancelled'].includes(appointment.status)"
              class="action-btn action-btn--qr"
              title="Show QR check-in pass"
              @click="openQr"
            >
              ▦ QR Pass
            </button>

            <!-- Top Actions -->
            <div v-if="canEditOrCancel" class="action-buttons-row">
              <button
                class="action-btn action-btn--edit"
                @click="openReschedule"
              >
                <span class="lucide-calendar-clock"></span>
                Reschedule / Edit
              </button>

              <button
                class="action-btn action-btn--cancel"
                :disabled="cancelling"
                @click="cancelAppointment"
              >
                ✕ Cancel Visit
              </button>
            </div>

            <!-- Delete if cancelled or pending -->
            <button
              v-if="appointment.status !== 'Completed'"
              class="action-btn action-btn--delete"
              :disabled="deleting"
              @click="deleteAppointment"
              title="Delete Record"
            >
              🗑️ Delete
            </button>
          </div>
        </header>

        <!-- Main Content Grid -->
        <div class="content-grid">

          <!-- Left Column -->
          <div class="main-column">

            <!-- Schedule Card -->
            <section class="detail-card">
              <div class="card-title-row">
                <div class="icon-circle teal">
                  <span class="lucide-calendar-days"></span>
                </div>
                <div>
                  <h3>Consultation Schedule</h3>
                  <p>Date, confirmed time slot, and booking code</p>
                </div>
              </div>

              <div class="schedule-stats-row">
                <div class="schedule-stat">
                  <span class="stat-label">Date</span>
                  <strong class="stat-value">{{ formatDate(appointment.appointment_date) }}</strong>
                </div>
                <div class="schedule-stat">
                  <span class="stat-label">Time Slot</span>
                  <strong class="stat-value highlight">{{ formatTime(appointment.appointment_time) }}</strong>
                </div>
                <div class="schedule-stat">
                  <span class="stat-label">Slot Reference</span>
                  <strong class="stat-value font-mono">{{ appointment.slot || 'Standard' }}</strong>
                </div>
              </div>
            </section>

            <!-- Doctor Information -->
            <section class="detail-card">
              <div class="card-title-row">
                <div class="icon-circle blue">
                  <span class="lucide-stethoscope"></span>
                </div>
                <div>
                  <h3>Assigned Doctor</h3>
                  <p>Certified specialist handling your consultation</p>
                </div>
              </div>

              <div class="doctor-profile-box">
                <div class="doctor-avatar-circle">
                  {{ getInitials(appointment.doctor_info?.full_name || appointment.doctor_name || appointment.doctor) }}
                </div>
                <div class="doctor-profile-details">
                  <h4>Dr. {{ appointment.doctor_info?.full_name || appointment.doctor_name || appointment.doctor }}</h4>
                  <p class="specialty-text">
                    {{ appointment.doctor_info?.specialty || appointment.doctor_specialty || 'General Practitioner' }}
                    <span v-if="appointment.doctor_info?.qualification"> • {{ appointment.doctor_info.qualification }}</span>
                  </p>
                  <div class="doctor-meta-chips">
                    <span v-if="appointment.doctor_info?.experience_years">
                      ⏱ {{ appointment.doctor_info.experience_years }} years exp
                    </span>
                    <span v-if="appointment.doctor_info?.rating">
                      ★ {{ appointment.doctor_info.rating }} rating
                    </span>
                    <span v-if="appointment.doctor_info?.phone">
                      📞 {{ appointment.doctor_info.phone }}
                    </span>
                  </div>
                  <p v-if="appointment.doctor_info?.bio" class="doctor-bio">
                    "{{ appointment.doctor_info.bio }}"
                  </p>
                </div>
              </div>
            </section>

            <!-- Reason for Visit -->
            <section class="detail-card">
              <div class="card-title-row">
                <div class="icon-circle amber">
                  <span class="lucide-message-square"></span>
                </div>
                <div>
                  <h3>Reason for Visit</h3>
                  <p>Chief complaint or notes provided during booking</p>
                </div>
              </div>

              <div class="reason-content-box">
                <p v-if="appointment.reason">{{ appointment.reason }}</p>
                <p v-else class="text-slate-400 italic">No specific reason provided at booking time.</p>
              </div>
            </section>

            <!-- Clinical Examination & Doctor Diagnosis (If Conducted) -->
            <section v-if="appointment.diagnosis || appointment.symptoms || appointment.treatment_plan || appointment.consultation_notes" class="detail-card clinical-card">
              <div class="card-title-row">
                <div class="icon-circle purple">
                  <span class="lucide-clipboard-check"></span>
                </div>
                <div>
                  <h3>Doctor's Clinical Notes & Diagnosis</h3>
                  <p>Recorded by Dr. {{ appointment.doctor_info?.full_name || appointment.doctor_name || 'your doctor' }}</p>
                </div>
              </div>

              <div class="clinical-grid">
                <div v-if="appointment.diagnosis" class="clinical-item">
                  <span class="c-label">Primary Diagnosis</span>
                  <div class="c-val diagnosis-val">{{ appointment.diagnosis }}</div>
                </div>

                <div v-if="appointment.symptoms" class="clinical-item">
                  <span class="c-label">Symptoms Noted</span>
                  <div class="c-val">{{ appointment.symptoms }}</div>
                </div>

                <div v-if="appointment.treatment_plan" class="clinical-item">
                  <span class="c-label">Treatment Plan</span>
                  <div class="c-val" v-html="appointment.treatment_plan"></div>
                </div>

                <div v-if="appointment.consultation_notes" class="clinical-item">
                  <span class="c-label">Doctor's Consultation Notes</span>
                  <div class="c-val" v-html="appointment.consultation_notes"></div>
                </div>

                <div v-if="appointment.follow_up_date" class="clinical-item follow-up-item">
                  <span class="c-label">Follow-up Appointment</span>
                  <div class="c-val">
                    📅 {{ formatDate(appointment.follow_up_date) }}
                    <span v-if="appointment.follow_up_instructions"> — {{ appointment.follow_up_instructions }}</span>
                  </div>
                </div>
              </div>
            </section>

            <!-- Prescriptions & Prescribed Medicines (If Issued) -->
            <section v-if="appointment.prescriptions && appointment.prescriptions.length" class="detail-card prescription-card">
              <div class="card-title-row">
                <div class="icon-circle teal">
                  <span class="lucide-pill"></span>
                </div>
                <div>
                  <h3>Prescription & Medicines</h3>
                  <p>Medication prescribed for this consultation</p>
                </div>
              </div>

              <div v-for="prx in appointment.prescriptions" :key="prx.name" class="prescription-block">
                <div class="prx-header">
                  <div>
                    <strong>Prescription #{{ prx.name }}</strong>
                    <span class="text-xs text-slate-500 ml-2">Issued {{ formatDate(prx.prescription_date) }}</span>
                  </div>
                  <span class="prx-status">{{ prx.status }}</span>
                </div>

                <div v-if="prx.medicines && prx.medicines.length" class="meds-table-wrapper">
                  <table class="meds-table">
                    <thead>
                      <tr>
                        <th>Medicine</th>
                        <th>Dosage</th>
                        <th>Frequency</th>
                        <th>Duration</th>
                        <th>Schedule / Times</th>
                        <th>Instructions</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="m in prx.medicines" :key="m.name">
                        <td class="font-bold text-slate-900">{{ m.prescribed_medicine_name || m.medicine }}</td>
                        <td>{{ m.dosage }}</td>
                        <td><span class="freq-tag">{{ m.frequency }}</span></td>
                        <td>{{ formatDate(m.start_date) }} to {{ formatDate(m.end_date) }}</td>
                        <td>
                          <div class="dose-times-list">
                            <span v-if="m.dose_time_1" class="time-tag">🌅 {{ formatTime(m.dose_time_1) }}</span>
                            <span v-if="m.dose_time_2" class="time-tag">☀️ {{ formatTime(m.dose_time_2) }}</span>
                            <span v-if="m.dose_time_3" class="time-tag">🌆 {{ formatTime(m.dose_time_3) }}</span>
                            <span v-if="m.dose_time_4" class="time-tag">🌙 {{ formatTime(m.dose_time_4) }}</span>
                          </div>
                        </td>
                        <td class="text-xs text-slate-600">{{ m.instructions || '—' }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </section>

            <!-- Lab / Diagnostic Reports -->
            <section v-if="appointment.reports && appointment.reports.length" class="detail-card reports-card">
              <div class="card-title-row">
                <div class="icon-circle purple">
                  <span class="lucide-file-text"></span>
                </div>
                <div>
                  <h3>Reports</h3>
                  <p>Lab, imaging and diagnostic results for this visit</p>
                </div>
              </div>
              <div v-for="rp in appointment.reports" :key="rp.name" class="report-row">
                <div class="report-info">
                  <strong>{{ rp.title }}</strong>
                  <span class="report-sub">{{ rp.report_type }}
                    <template v-if="rp.laboratory"> · {{ rp.laboratory }}</template>
                    <template v-if="rp.external"> · External</template>
                  </span>
                  <p v-if="rp.findings" class="report-findings">{{ rp.findings }}</p>
                </div>
                <div class="report-side">
                  <span class="report-status" :class="`report-status--${(rp.status || '').toLowerCase()}`">{{ rp.status }}</span>
                  <a v-if="rp.report_file" :href="rp.report_file" target="_blank" class="report-open">Open ↗</a>
                </div>
              </div>
            </section>

            <!-- Referral episode banner -->
            <section v-if="appointment.referral" class="detail-card referral-banner">
              <div class="card-title-row">
                <div class="icon-circle purple"><span>🤝</span></div>
                <div>
                  <h3>Referral episode · {{ appointment.referral.name }}</h3>
                  <p>{{ appointment.referral.status }} · {{ appointment.referral.specialty || 'Specialist' }}</p>
                </div>
              </div>
              <p class="referral-reason"><strong>Reason:</strong> {{ appointment.referral.reason }}</p>
            </section>

          </div>

          <!-- Right Column -->
          <aside class="sidebar-column">

            <!-- Payment Fee Card -->
            <section class="detail-card payment-sidebar-card">
              <div class="card-title-row">
                <div class="icon-circle teal">
                  <span>₹</span>
                </div>
                <div>
                  <h3>Consultation Fee</h3>
                  <p>Billing & payment status</p>
                </div>
              </div>

              <div class="fee-display">
                {{ formatFee(appointment.consultation_fee) }}
              </div>

              <div
                class="payment-pill"
                :class="appointment.payment_status?.toLowerCase() === 'paid' ? 'paid' : 'pending'"
              >
                {{ appointment.payment_status || 'Pending' }}
              </div>
            </section>

            <!-- AI Consultation Summary (completed visits only) -->
            <section v-if="appointment.status === 'Completed'" class="detail-card ai-summary-card">
              <div class="card-title-row">
                <div class="icon-circle purple"><span>🤖</span></div>
                <div>
                  <h3>AI Consultation Summary</h3>
                  <p>Plain-language recap of this visit</p>
                </div>
              </div>
              <p class="ai-summary-teaser">
                Understand what Dr.
                {{ appointment.doctor_info?.full_name || appointment.doctor_name || 'your doctor' }}
                diagnosed, the medicines prescribed, and what to do next.
              </p>
              <button
                class="btn-primary ai-summary-btn"
                :disabled="aiSummaryLoading"
                @click="openAiSummary"
              >
                🤖 {{ aiSummaryLoading ? 'Generating…' : 'View AI Summary' }}
              </button>
            </section>

            <!-- Check-in & Queue Pass -->
            <section v-if="!['Completed', 'Cancelled'].includes(appointment.status)" class="detail-card queue-pass-card">
              <div class="card-title-row">
                <div class="icon-circle amber"><span>▦</span></div>
                <div>
                  <h3>Check-in & Queue</h3>
                  <p>Show this pass at reception to join the doctor's queue</p>
                </div>
              </div>

              <div class="qr-box">
                <div v-if="qrLoading" class="qr-placeholder">Generating QR pass…</div>
                <div v-else-if="qrImgBroken && appointment.qr_code" class="qr-placeholder">
                  QR image failed to load.
                  <button class="btn-secondary" @click="retryQrImage">Retry</button>
                </div>
                <img
                  v-else-if="appointment.qr_data_url || appointment.qr_code"
                  :src="appointment.qr_data_url || appointment.qr_code"
                  alt="Appointment QR code"
                  class="qr-img"
                  @error="qrImgBroken = true"
                  @load="qrImgBroken = false"
                />
                <div v-else class="qr-placeholder">{{ qrError || 'QR pass unavailable' }}</div>
                <div class="qr-actions">
                  <button class="btn-secondary" @click="openQr">View Full Size</button>
                  <button class="btn-secondary" :disabled="qrLoading" @click="downloadQr">⬇ Download QR</button>
                </div>
              </div>

              <div class="queue-status-rows">
                <div class="queue-status-row">
                  <span>Check-in</span>
                  <strong :class="appointment.checked_in ? 'ok' : ''">
                    {{ appointment.checked_in ? '✅ Checked In' : 'Not checked in' }}
                  </strong>
                </div>
                <div v-if="appointment.queue_token" class="queue-status-row">
                  <span>Token</span>
                  <strong>#{{ appointment.queue_token }}</strong>
                </div>
                <div v-if="appointment.visit_stage" class="queue-status-row">
                  <span>Stage</span>
                  <strong>{{ appointment.visit_stage }}</strong>
                </div>
                <div v-if="queueInfo?.queue_position" class="queue-status-row">
                  <span>Position in queue</span>
                  <strong>{{ queueInfo.queue_position }}</strong>
                </div>
                <div v-if="queueInfo?.patients_ahead != null" class="queue-status-row">
                  <span>Patients ahead</span>
                  <strong>{{ queueInfo.patients_ahead }}</strong>
                </div>
                <div v-if="queueInfo?.estimated_wait_minutes != null" class="queue-status-row">
                  <span>Estimated wait</span>
                  <strong>~{{ queueInfo.estimated_wait_minutes }} min</strong>
                </div>
                <div v-if="queueInfo?.average_wait_minutes" class="queue-status-row">
                  <span>Average wait today</span>
                  <strong>{{ queueInfo.average_wait_minutes }} min</strong>
                </div>
              </div>
            </section>

            <!-- Patient Profile Card -->
            <section class="detail-card">
              <div class="card-title-row">
                <div class="icon-circle blue">
                  <span class="lucide-user"></span>
                </div>
                <div>
                  <h3>Patient Details</h3>
                  <p>Account profile</p>
                </div>
              </div>

              <div class="patient-info-rows">
                <div class="info-row">
                  <span class="row-label">Name</span>
                  <span class="row-value">{{ appointment.patient_info?.full_name || appointment.patient_name || appointment.patient }}</span>
                </div>
                <div v-if="appointment.patient_info?.phone" class="info-row">
                  <span class="row-label">Phone</span>
                  <span class="row-value">{{ appointment.patient_info.phone }}</span>
                </div>
                <div v-if="appointment.patient_info?.age" class="info-row">
                  <span class="row-label">Age</span>
                  <span class="row-value">{{ appointment.patient_info.age }} years</span>
                </div>
                <div v-if="appointment.patient_info?.gender" class="info-row">
                  <span class="row-label">Gender</span>
                  <span class="row-value">{{ appointment.patient_info.gender }}</span>
                </div>
              </div>
            </section>

            <!-- Quick Guidelines -->
            <section v-if="appointment.status !== 'Completed'" class="detail-card guidelines-card">
              <h4>Patient Checklist</h4>
              <ul class="guidelines-list">
                <li>Arrive or be available online 10 minutes before {{ formatTime(appointment.appointment_time) }}.</li>
                <li>Have previous medical reports and prescriptions ready for Dr. {{ appointment.doctor_info?.full_name || appointment.doctor_name || 'Doctor' }}.</li>
                <li>You can reschedule or cancel anytime up to 15 minutes before the visit.</li>
              </ul>
            </section>

          </aside>

        </div>

      </div>

    </div>

    <!-- QR Pass Modal -->
    <div v-if="showQrModal" class="modal-backdrop" @click.self="showQrModal = false">
      <div class="modal-card qr-modal-card">
        <div class="modal-header">
          <div>
            <h3>Check-in QR Pass</h3>
            <p class="modal-subtitle">
              Appointment #{{ appointment?.name }} · {{ formatDate(appointment?.appointment_date) }}
              · {{ formatTime(appointment?.appointment_time) }}
            </p>
          </div>
          <button class="modal-close" @click="showQrModal = false">✕</button>
        </div>
        <div class="qr-modal-body">
          <div v-if="qrLoading" class="qr-placeholder">Generating QR pass…</div>
          <div v-else-if="qrImgBroken && appointment?.qr_code" class="qr-placeholder">
            QR image failed to load.
            <button class="btn-secondary" @click="retryQrImage">Retry</button>
          </div>
          <img
            v-else-if="appointment?.qr_data_url || appointment?.qr_code"
            :src="appointment.qr_data_url || appointment.qr_code"
            alt="Appointment QR code"
            class="qr-img qr-img--lg"
            @error="qrImgBroken = true"
            @load="qrImgBroken = false"
          />
          <div v-else class="qr-placeholder">{{ qrError || 'QR pass unavailable' }}</div>
          <p class="qr-hint">
            Let the receptionist scan this code at the clinic to check you in and add you to
            Dr. {{ appointment?.doctor_info?.full_name || appointment?.doctor_name || 'Doctor' }}'s queue.
          </p>
          <button class="btn-primary" :disabled="qrLoading" @click="downloadQr">⬇ Download QR</button>
        </div>
      </div>
    </div>

    <!-- AI SUMMARY MODAL -->
    <div v-if="showAiSummaryModal" class="modal-backdrop" @click.self="showAiSummaryModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <div>
            <h3>🤖 AI Consultation Summary</h3>
            <p class="modal-subtitle">
              Appointment #{{ appointment?.name }} · {{ formatDate(appointment?.appointment_date) }}
            </p>
          </div>
          <button class="modal-close" @click="showAiSummaryModal = false">✕</button>
        </div>
        <div class="modal-body">
          <div v-if="aiSummaryLoading" class="ai-loading">
            <span class="ai-spinner"></span>
            Generating a patient-friendly summary…
          </div>
          <div v-else-if="aiSummaryError" class="ai-error">{{ aiSummaryError }}</div>
          <template v-else-if="aiSummary">
            <p v-if="aiSummary.summary" class="ai-summary-text">{{ aiSummary.summary }}</p>
            <div v-if="aiSummary.key_points && aiSummary.key_points.length" class="ai-block">
              <h4>Key Points</h4>
              <ul>
                <li v-for="(k, i) in aiSummary.key_points" :key="'k' + i">{{ k }}</li>
              </ul>
            </div>
            <div v-if="aiSummary.next_steps && aiSummary.next_steps.length" class="ai-block">
              <h4>Next Steps</h4>
              <ul>
                <li v-for="(n, i) in aiSummary.next_steps" :key="'n' + i">{{ n }}</li>
              </ul>
            </div>
            <div v-if="aiSummary.medicines && aiSummary.medicines.length" class="ai-block">
              <h4>Medicines</h4>
              <ul>
                <li v-for="(m, i) in aiSummary.medicines" :key="'m' + i">
                  {{ m.prescribed_medicine_name || 'Medicine' }}
                  — {{ m.dosage }}<template v-if="m.frequency"> · {{ m.frequency }}</template>
                </li>
              </ul>
            </div>
            <p class="ai-note">
              AI-generated summary — for guidance only. Always follow your doctor's advice.
            </p>
          </template>
          <button
            class="btn-secondary ai-close"
            style="margin-top: 14px;"
            @click="showAiSummaryModal = false"
          >
            Close
          </button>
        </div>
      </div>
    </div>

    <!-- Reschedule / Edit Modal -->
    <div v-if="showRescheduleModal" class="modal-backdrop" @click.self="showRescheduleModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <div>
            <h3>Reschedule Appointment #{{ appointment.name }}</h3>
            <p class="text-xs text-slate-500">Pick a new date and time with Dr. {{ appointment.doctor_info?.full_name || appointment.doctor_name }}</p>
          </div>
          <button class="close-btn" @click="showRescheduleModal = false">✕</button>
        </div>

        <div class="modal-body">
          <div v-if="rescheduleError" class="modal-error">
            {{ rescheduleError }}
          </div>

          <!-- Date Picker -->
          <div class="form-group mb-4">
            <label class="form-label">Select New Date *</label>
            <input
              v-model="rescheduleDate"
              type="date"
              class="form-input"
              @change="fetchAvailableSlots"
            />
          </div>

          <!-- Slot Picker -->
          <div class="form-group mb-4">
            <label class="form-label">Select Available Time Slot *</label>
            <div v-if="loadingSlots" class="text-xs text-slate-500 py-3 text-center">
              Loading available slots...
            </div>
            <div v-else-if="!availableSlots.length" class="empty-slots-box">
              No available slots on this date. Please choose another day.
            </div>
            <div v-else class="slots-grid">
              <button
                v-for="s in availableSlots"
                :key="s.start_time"
                type="button"
                class="slot-btn"
                :class="{ active: rescheduleTime === s.start_time }"
                @click="rescheduleTime = s.start_time"
              >
                {{ s.formatted }}
              </button>
            </div>
          </div>

          <!-- Reason Edit -->
          <div class="form-group">
            <label class="form-label">Reason for Visit / Update Notes</label>
            <textarea
              v-model="rescheduleReason"
              rows="3"
              class="form-textarea"
              placeholder="e.g. Need to reschedule due to schedule conflict, headache follow-up..."
            ></textarea>
          </div>
        </div>

        <div class="modal-footer">
          <button
            class="btn-secondary"
            @click="showRescheduleModal = false"
          >
            Cancel
          </button>
          <button
            class="btn-primary"
            :disabled="rescheduling || !rescheduleDate || !rescheduleTime"
            @click="submitReschedule"
          >
            {{ rescheduling ? 'Rescheduling...' : 'Confirm Reschedule' }}
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.appointment-page {
  min-height: 100vh;
  padding: 32px 32px 64px;
  background:
    radial-gradient(circle at 10% 8%, rgba(13, 148, 136, 0.08), transparent 32%),
    radial-gradient(circle at 90% 12%, rgba(37, 99, 235, 0.06), transparent 30%),
    #f4f7fb;
  color: #0f172a;
}

.page-container {
  max-width: 1160px;
  margin: 0 auto;
}

.back-link {
  background: none;
  border: none;
  font-size: 13px;
  font-weight: 700;
  color: #0d9488;
  cursor: pointer;
  padding: 0;
  margin-bottom: 12px;
  display: inline-flex;
  align-items: center;
  transition: color 0.15s;
}

.back-link:hover { color: #0f766e; }

.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 1.2px;
  text-transform: uppercase;
  color: #0d9488;
  margin-bottom: 6px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 28px;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.8);
}

.page-header h1 {
  font-size: clamp(26px, 3.2vw, 36px);
  font-weight: 800;
  letter-spacing: -1.2px;
  margin: 0 0 6px;
  color: #0f172a;
}

.page-header h1 span { color: #0d9488; }
.created-text { font-size: 13px; color: #64748b; margin: 0; }

.header-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
}

.action-buttons-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 700;
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.15s;
}

.action-btn--edit {
  background: #0d9488;
  color: white;
}
.action-btn--edit:hover { background: #0f766e; box-shadow: 0 4px 12px rgba(13, 148, 136, 0.25); }

.action-btn--cancel {
  background: white;
  border-color: #fecaca;
  color: #b91c1c;
}
.action-btn--cancel:hover { background: #fef2f2; }

.action-btn--delete {
  background: none;
  border: none;
  color: #94a3b8;
  font-size: 12px;
  padding: 4px 8px;
}
.action-btn--delete:hover { color: #ef4444; }

/* Status pill */
.status-pill {
  font-size: 12px;
  font-weight: 800;
  padding: 5px 14px;
  border-radius: 999px;
  text-transform: capitalize;
  letter-spacing: 0.3px;
}
.status-pending   { background: #fef3c7; color: #b45309; }
.status-confirmed { background: #d1fae5; color: #047857; }
.status-completed { background: #dbeafe; color: #1e40af; }
.status-cancelled { background: #fee2e2; color: #b91c1c; }

/* Content grid */
.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 24px;
}

.main-column, .sidebar-column {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Detail Card */
.detail-card {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
}

.card-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
}

.icon-circle {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}
.icon-circle.teal   { background: rgba(13, 148, 136, 0.12); color: #0d9488; }
.icon-circle.blue   { background: rgba(37, 99, 235, 0.12);  color: #2563eb; }
.icon-circle.amber  { background: rgba(245, 158, 11, 0.12); color: #d97706; }
.icon-circle.purple { background: rgba(124, 58, 237, 0.12); color: #7c3aed; }

.card-title-row h3 {
  font-size: 16px;
  font-weight: 800;
  color: #0f172a;
  margin: 0 0 2px;
}

.card-title-row p {
  font-size: 12px;
  color: #64748b;
  margin: 0;
}

/* Schedule stats */
.schedule-stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  background: #f8fafc;
  padding: 14px 16px;
  border-radius: 14px;
}

.schedule-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.stat-label { font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase; }
.stat-value { font-size: 14px; font-weight: 700; color: #0f172a; }
.stat-value.highlight { color: #0d9488; }

/* Doctor Profile Box */
.doctor-profile-box {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.doctor-avatar-circle {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  background: linear-gradient(135deg, #0d9488 0%, #2563eb 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 800;
  box-shadow: 0 6px 16px rgba(13, 148, 136, 0.25);
  flex-shrink: 0;
}

.doctor-profile-details h4 {
  font-size: 17px;
  font-weight: 800;
  color: #0f172a;
  margin: 0 0 3px;
}

.specialty-text { font-size: 13px; color: #0d9488; font-weight: 600; margin: 0 0 8px; }

.doctor-meta-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 11px;
  color: #64748b;
  font-weight: 600;
  margin-bottom: 8px;
}

.doctor-meta-chips span {
  background: #f1f5f9;
  padding: 3px 8px;
  border-radius: 6px;
}

.doctor-bio {
  font-size: 12px;
  color: #475569;
  font-style: italic;
  margin: 0;
  line-height: 1.4;
}

/* Reason box */
.reason-content-box {
  background: #f8fafc;
  padding: 14px 16px;
  border-radius: 14px;
  font-size: 13px;
  color: #334155;
  line-height: 1.5;
}

/* Clinical Grid */
.clinical-grid {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.clinical-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f1f5f9;
}
.clinical-item:last-child { border-bottom: none; padding-bottom: 0; }

.c-label { font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; }
.c-val { font-size: 13px; color: #1e293b; line-height: 1.5; }
.diagnosis-val { font-size: 15px; font-weight: 800; color: #0d9488; }
.follow-up-item { background: #f0fdfa; padding: 12px 14px; border-radius: 12px; }

/* Prescription */
.prescription-block {
  margin-top: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  overflow: hidden;
}

.prx-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f8fafc;
  padding: 10px 14px;
  border-bottom: 1px solid #e2e8f0;
  font-size: 13px;
}
.prx-status { font-size: 11px; font-weight: 700; color: #0d9488; background: #ccfbf1; padding: 2px 8px; border-radius: 6px; }

.meds-table-wrapper { overflow-x: auto; }
.meds-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  text-align: left;
}
.meds-table th, .meds-table td {
  padding: 10px 12px;
  border-bottom: 1px solid #f1f5f9;
}
.meds-table th { background: #fcfcfd; color: #64748b; font-weight: 700; }
.freq-tag { background: #eff6ff; color: #2563eb; padding: 2px 6px; border-radius: 6px; font-weight: 600; font-size: 11px; }

.dose-times-list { display: flex; flex-wrap: wrap; gap: 4px; }
.time-tag { background: #f1f5f9; font-size: 10px; font-weight: 600; padding: 2px 5px; border-radius: 4px; }

/* Sidebar payment */
.fee-display {
  font-size: 32px;
  font-weight: 800;
  color: #0d9488;
  margin-bottom: 10px;
}

.payment-pill {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 999px;
  text-transform: uppercase;
}
.payment-pill.paid { background: #d1fae5; color: #047857; }
.payment-pill.pending { background: #fef3c7; color: #b45309; }

/* Patient info rows */
.patient-info-rows { display: flex; flex-direction: column; gap: 8px; }
.info-row { display: flex; justify-content: space-between; font-size: 12px; border-bottom: 1px solid #f8fafc; padding-bottom: 6px; }
.row-label { color: #64748b; }
.row-value { font-weight: 700; color: #0f172a; }

/* Guidelines */
.guidelines-card h4 { font-size: 13px; font-weight: 700; color: #0f172a; margin: 0 0 8px; }
.guidelines-list { margin: 0; padding-left: 18px; font-size: 12px; color: #64748b; line-height: 1.6; }

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
.modal-header h3 { font-size: 16px; font-weight: 800; color: #0f172a; margin: 0 0 2px; }
.close-btn { background: none; border: none; font-size: 16px; color: #94a3b8; cursor: pointer; }

.modal-body { padding: 20px 24px; overflow-y: auto; flex: 1; }
.modal-error { background: #fef2f2; border: 1px solid #fecaca; color: #b91c1c; font-size: 12px; padding: 10px 12px; border-radius: 10px; margin-bottom: 14px; }

.form-label { display: block; font-size: 12px; font-weight: 700; color: #475569; margin-bottom: 6px; }
.form-input, .form-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  font-size: 13px;
  color: #0f172a;
  outline: none;
}
.form-input:focus, .form-textarea:focus { border-color: #0d9488; box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.12); }

.slots-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(90px, 1fr));
  gap: 8px;
  max-height: 180px;
  overflow-y: auto;
  padding: 4px;
}

.slot-btn {
  padding: 8px 4px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: white;
  font-size: 12px;
  font-weight: 600;
  color: #334155;
  cursor: pointer;
  transition: all 0.15s;
}
.slot-btn:hover { border-color: #0d9488; color: #0d9488; }
.slot-btn.active { background: #0d9488; color: white; border-color: #0d9488; }

.empty-slots-box { padding: 14px; background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 10px; text-align: center; font-size: 12px; color: #64748b; }

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid #f1f5f9;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.btn-primary {
  padding: 9px 18px;
  background: #0d9488;
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-secondary {
  padding: 9px 16px;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  cursor: pointer;
}

/* State */
.state-card {
  padding: 60px 20px;
  text-align: center;
  background: white;
  border-radius: 20px;
  border: 1px dashed #cbd5e1;
}

.loader {
  width: 32px;
  height: 32px;
  border: 3px solid #e2e8f0;
  border-top-color: #0d9488;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 12px;
}
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 860px) {
  .content-grid { grid-template-columns: 1fr; }
  .page-header { flex-direction: column; align-items: flex-start; }
  .header-right { align-items: flex-start; }
}
/* Reports + referral (appointment detail) */
.report-row { display: flex; justify-content: space-between; gap: 14px; align-items: flex-start; padding: 12px 14px; border: 1px solid #e2e8f0; border-radius: 10px; margin-bottom: 10px; background: #fafcff; }
.report-info strong { font-size: 14px; color: #0f172a; display: block; }
.report-sub { font-size: 12px; color: #64748b; }
.report-findings { font-size: 13px; color: #334155; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 10px; margin: 8px 0 0; }
.report-side { display: flex; flex-direction: column; align-items: flex-end; gap: 6px; flex-shrink: 0; }
.report-status { font-size: 11px; font-weight: 700; padding: 3px 9px; border-radius: 999px; background: #f1f5f9; color: #475569; white-space: nowrap; }
.report-status--uploaded { background: #d1fae5; color: #065f46; }
.report-status--reviewed { background: #dbeafe; color: #1e40af; }
.report-status--ordered { background: #ede9fe; color: #5b21b6; }
.report-status--pending { background: #fef3c7; color: #92400e; }
.report-open { font-size: 13px; font-weight: 700; color: #0d9488; text-decoration: none; }
.referral-reason { font-size: 13px; color: #334155; background: #f0fdfa; border: 1px solid #99f6e4; border-radius: 8px; padding: 10px 12px; margin: 0; }

/* Priority badges + QR pass */
.priority-pill {
  font-size: 11px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 999px;
  white-space: nowrap;
}
.priority-pill--fast { background: #fee2e2; color: #b91c1c; border: 1px solid #fecaca; }
.priority-pill--return { background: #dbeafe; color: #1e40af; border: 1px solid #bfdbfe; }
.priority-pill--high { background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }
.action-btn--qr {
  background: #0f172a;
  color: #fff;
  border: none;
  border-radius: 10px;
  padding: 8px 14px;
  font-size: 12.5px;
  font-weight: 700;
  cursor: pointer;
}
.action-btn--qr:hover { background: #1e293b; }

.queue-pass-card .qr-box { text-align: center; margin-bottom: 14px; }
.qr-img {
  width: 160px;
  height: 160px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: #fff;
  object-fit: contain;
  display: inline-block;
}
.qr-img--lg { width: 240px; height: 240px; }
.qr-placeholder {
  width: 160px;
  min-height: 120px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  font-size: 12px;
  color: #64748b;
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 12px;
  padding: 10px;
}
.qr-actions { display: flex; gap: 8px; justify-content: center; margin-top: 10px; flex-wrap: wrap; }

.queue-status-rows { display: flex; flex-direction: column; gap: 8px; }
.queue-status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 10px;
}
.queue-status-row span { color: #64748b; }
.queue-status-row strong { color: #0f172a; }
.queue-status-row strong.ok { color: #047857; }

.qr-modal-card { max-width: 420px; }
.qr-modal-body { padding: 20px 24px 24px; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 12px; }
.qr-hint { font-size: 13px; color: #475569; margin: 0; }
.modal-subtitle { font-size: 12.5px; color: #64748b; margin: 4px 0 0; }

/* ---------- AI consultation summary (patient view) ---------- */
.ai-summary-teaser { font-size: 13px; color: #64748b; line-height: 1.55; margin: 0 0 12px; }
.ai-summary-btn { width: 100%; justify-content: center; }
.ai-loading { display: flex; align-items: center; gap: 10px; color: #64748b; font-size: 13px; padding: 8px 0; }
.ai-spinner {
  width: 16px; height: 16px; border-radius: 50%;
  border: 2px solid #cbd5e1; border-top-color: #0d9488;
  animation: ai-spin 0.8s linear infinite; display: inline-block;
}
@keyframes ai-spin { to { transform: rotate(360deg); } }
.ai-error {
  font-size: 13px; color: #b91c1c; background: #fef2f2;
  border: 1px solid #fecaca; border-radius: 10px; padding: 10px 12px;
}
.ai-summary-text {
  font-size: 14px; line-height: 1.6; color: #0f172a; background: #f8fafc;
  border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px 14px; margin: 0 0 14px;
}
.ai-block { margin-bottom: 14px; }
.ai-block h4 {
  font-size: 12px; font-weight: 800; color: #0d9488; margin: 0 0 6px;
  text-transform: uppercase; letter-spacing: 0.04em;
}
.ai-block ul { margin: 0; padding-left: 18px; font-size: 13px; color: #334155; }
.ai-block li { margin-bottom: 4px; }
.ai-note {
  font-size: 11.5px; color: #92400e; background: #fffbeb;
  border: 1px solid #fde68a; border-radius: 8px; padding: 8px 10px; margin: 0;
}
</style>