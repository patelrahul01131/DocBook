<script setup>
import { computed, onMounted, ref } from 'vue'
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
            <section class="detail-card guidelines-card">
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
</style>