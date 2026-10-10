<template>

<Dialog
  v-model:open="showBookingDialog"
  size="lg"
  :title="bookingDialogTitle"
  :dismissible="bookingStep === 2"
>
  <!-- Progress -->
  <div class="booking-progress">
    <span
      v-for="(_, index) in bookingSteps"
      :key="index"
      class="progress-item"
      :class="{ active: index <= bookingStep }"
    ></span>
  </div>

  <!-- STEP 1: Appointment details -->
  <div
    v-if="bookingStep === 0"
    class="booking-form"
  >
    <div class="booking-doctor">

      <div>
        <span>BOOKING WITH</span>

        <strong>
          Dr. {{ doctor?.full_name }}
        </strong>
      </div>
    </div>

    <div class="form-grid">

      <div class="form-group">
        <label>Appointment Date</label>

        <input
          v-model="bookingForm.appointment_date"
          type="date"
          :min="today"
          class="date-input"
        />
      </div>

      <div class="form-group">
        <label>Appointment Time</label>

        <input
          v-model="bookingForm.appointment_time"
          type="time"
        />
      </div>

    </div>

    <div class="fee-preview">
      <span>Consultation Fee</span>

      <strong>
        ₹{{ doctor?.consultation_fee || 0 }}
      </strong>
    </div>
  </div>


  <!-- STEP 2: Reason -->
  <div
    v-else-if="bookingStep === 1"
    class="booking-form"
  >

    <div class="form-heading">
      <div class="dialog-icon">
        🩺
      </div>

      <div>
        <h3>
          Reason for Visit
        </h3>

        <p>
          Tell the doctor briefly why you are booking this consultation.
        </p>
      </div>
    </div>

    <div class="form-group">
      <label>Reason for Visit</label>

      <textarea
        v-model="bookingForm.reason"
        rows="5"
        placeholder="Example: General consultation, headache, follow-up..."
      ></textarea>
    </div>

  </div>


  <!-- STEP 3: Review -->
  <div
    v-else
    class="booking-review"
  >

    <div class="review-icon">
      ✓
    </div>

    <h3>
      Review Appointment
    </h3>

    <p>
      Please check your appointment details before booking.
    </p>

    <div class="review-card">

      <div class="review-row">
        <span>Doctor</span>

        <strong>
          Dr. {{ doctor?.full_name }}
        </strong>
      </div>

      <div class="review-row">
        <span>Date</span>

        <strong>
          {{ bookingForm.appointment_date }}
        </strong>
      </div>

      <div class="review-row">
        <span>Time</span>

        <strong>
          {{ bookingForm.appointment_time }}
        </strong>
      </div>

      <div class="review-row">
        <span>Reason</span>

        <strong>
          {{ bookingForm.reason || 'General consultation' }}
        </strong>
      </div>

      <div class="review-row total-row">
        <span>Consultation Fee</span>

        <strong>
          ₹{{ doctor?.consultation_fee || 0 }}
        </strong>
      </div>

    </div>

  </div>


  <!-- Actions -->
  <template #actions="{ close }">

    <div class="booking-actions">

      <!-- Back -->
      <Button
        v-if="bookingStep > 0 && bookingStep < 2"
        variant="subtle"
        @click="bookingStep -= 1"
      >
        Back
      </Button>

      <span v-else></span>


      <div class="booking-action-right">

        <!-- Cancel -->
        <Button
          v-if="bookingStep < 2"
          variant="subtle"
          @click="close"
        >
          Cancel
        </Button>


        <!-- Continue -->
        <Button
          v-if="bookingStep < 2"
          variant="solid"
          :disabled="!canContinueBooking"
          @click="nextBookingStep"
        >
          {{ bookingStep === 1 ? 'Review Appointment' : 'Continue' }}
        </Button>


        <!-- Final booking -->
        <Button
          v-else
          variant="solid"
          :loading="bookingLoading"
          @click="confirmBooking(close)"
        >
          Book Appointment
        </Button>

      </div>

    </div>

  </template>
</Dialog>


  <div class="doctor-page">

    <!-- Background decoration -->
    <div class="bg-orb orb-blue"></div>
    <div class="bg-orb orb-teal"></div>

    <!-- Main container -->
    <main class="page-container">

      <!-- Page Header -->
      <div class="page-header">

        <div>
          <span class="eyebrow">
            DOCTOR PROFILE
          </span>

          <h1>
            Doctor Profile
          </h1>

          <p>
            View doctor information and book your consultation.
          </p>
        </div>

        <button
          class="header-back-button"
          @click="$router.back()"
        >
          <span>←</span>
          Back
        </button>

      </div>


      <!-- Loading -->
      <div
        v-if="!doctor && route.query.doctor"
        class="loading-card"
      >
        <div class="loader"></div>

        <div>
          <h3>Loading doctor profile...</h3>
          <p>Please wait a moment.</p>
        </div>
      </div>


      <!-- No Doctor -->
      <div
        v-else-if="!doctor"
        class="empty-card"
      >
        <div class="empty-icon">
          🩺
        </div>

        <h2>
          No doctor selected
        </h2>

        <p>
          Please select a doctor to view their profile.
        </p>

        <button
          class="primary-button"
          @click="$router.push('/find-doctors')"
        >
          Find a Doctor
        </button>
      </div>


      <!-- Doctor Profile -->
      <div
        v-else
        class="profile-layout"
      >

        <!-- Left / Main Profile -->
        <section class="profile-card">

          <!-- Profile Hero -->
          <div class="profile-hero">

            <div class="doctor-avatar-wrapper">

              <div class="doctor-avatar">
                {{ doctor.full_name?.charAt(0).toUpperCase() }}
              </div>

              <span
                v-if="doctor.is_approved"
                class="online-dot"
              ></span>

            </div>


            <div class="doctor-main-info">

              <div class="name-row">

                <h2>
                  Dr. {{ doctor.full_name }}
                </h2>

                <span
                  v-if="doctor.is_approved"
                  class="verified-badge"
                >
                  <span>✓</span>
                  Verified
                </span>

              </div>

              <p class="doctor-title">
                Medical Doctor
              </p>

              <p class="doctor-email">
                {{ doctor.user }}
              </p>

            </div>

          </div>


          <!-- Rating -->
          <div class="rating-section">

            <div class="rating-main">

              <div class="rating-star">
                ★
              </div>

              <div>
                <div class="rating-number">
                  {{ doctor.rating || 0 }}
                  <span>/5</span>
                </div>

                <p>
                  Doctor Rating
                </p>
              </div>

            </div>

            <div class="rating-bars">

              <div class="rating-bar-row">
                <span>5</span>
                <div class="rating-bar">
                  <div
                    class="rating-fill"
                    :style="{
                      width: `${(doctor.rating / 5) * 100}%`
                    }"
                  ></div>
                </div>
              </div>

              <div class="rating-bar-row">
                <span>4</span>
                <div class="rating-bar">
                  <div class="rating-fill small"></div>
                </div>
              </div>

              <div class="rating-bar-row">
                <span>3</span>
                <div class="rating-bar">
                  <div class="rating-fill smaller"></div>
                </div>
              </div>

            </div>

          </div>


          <!-- Information -->
          <div class="section">

            <div class="section-heading">
              <div>
                <span class="section-eyebrow">
                  INFORMATION
                </span>

                <h3>
                  Doctor Details
                </h3>
              </div>
            </div>


            <div class="info-grid">

              <!-- Experience -->
              <div class="info-card">

                <div class="info-icon blue">
                  ⏱
                </div>

                <div class="info-content">
                  <span>
                    Experience
                  </span>

                  <strong>
                    {{ doctor.experience_years || 0 }}
                    <small>Years</small>
                  </strong>
                </div>

              </div>


              <!-- Consultation Fee -->
              <div class="info-card">

                <div class="info-icon teal">
                  ₹
                </div>

                <div class="info-content">
                  <span>
                    Consultation Fee
                  </span>

                  <strong>
                    ₹{{ doctor.consultation_fee || 0 }}
                  </strong>
                </div>

              </div>


              <!-- Email -->
              <div class="info-card">

                <div class="info-icon purple">
                  ✉
                </div>

                <div class="info-content">
                  <span>
                    Email
                  </span>

                  <strong class="email-value">
                    {{ doctor.user }}
                  </strong>
                </div>

              </div>


              <!-- Status -->
              <div class="info-card">

                <div class="info-icon green">
                  ✓
                </div>

                <div class="info-content">
                  <span>
                    Profile Status
                  </span>

                  <strong>
                    {{
                      doctor.is_approved
                        ? 'Approved'
                        : 'Pending'
                    }}
                  </strong>
                </div>

              </div>

            </div>

          </div>


          <!-- Account Information -->
          <div class="account-section">

            <div class="account-row">

              <div>
                <span>
                  Profile ID
                </span>

                <strong>
                  {{ doctor.name }}
                </strong>
              </div>

              <div>
                <span>
                  Account
                </span>

                <strong>
                  {{ doctor.user }}
                </strong>
              </div>

            </div>

          </div>

        </section>


        <!-- Right / Appointment Card -->
        <aside class="appointment-card">

          <div class="appointment-glow"></div>

          <div class="appointment-content">

            <div class="appointment-icon">
              🩺
            </div>

            <span class="appointment-label">
              BOOK CONSULTATION
            </span>

            <h2>
              Ready to book
              your appointment?
            </h2>

            <p>
              Choose a convenient time and schedule
              your consultation with Dr.
              {{ doctor.full_name }}.
            </p>


            <!-- Fee -->
            <div class="appointment-fee">

              <span>
                Consultation fee
              </span>

              <strong>
                ₹{{ doctor.consultation_fee || 0 }}
              </strong>

            </div>


            <!-- Button -->
            <button
              class="book-button"
              @click="openBookingDialog"
            >
              Book Appointment

              <span>
                →
              </span>
            </button>


            <p class="secure-text">
              🔒 Secure &amp; private booking
            </p>

          </div>

        </aside>

      </div>

    </main>

  </div>
</template>


<script setup>

import {
  computed,
  onMounted,
  reactive,
  ref
} from 'vue'

import {
  Dialog,
  Button
} from 'frappe-ui'

import {
  useRoute,
  useRouter
} from 'vue-router'

import { call } from '../../api'
import { useAuthStore } from '../../stores/auth'
import { toast } from 'frappe-ui'

const route = useRoute()
const router = useRouter()

const auth = useAuthStore()

const doctor = ref(null)

const showBookingDialog = ref(false)

const bookingStep = ref(0)

const bookingLoading = ref(false)


const bookingSteps = [
  'Appointment',
  'Reason',
  'Review'
]


const bookingForm = reactive({

  appointment_date: '',

  appointment_time: '',

  reason: ''

})


const today = computed(() => {

  const date = new Date()

  const year = date.getFullYear()

  const month =
    String(date.getMonth() + 1)
      .padStart(2, '0')

  const day =
    String(date.getDate())
      .padStart(2, '0')

  return `${year}-${month}-${day}`

})


const bookingDialogTitle = computed(() => {

  if (bookingStep.value === 0) {
    return 'Book Appointment'
  }

  if (bookingStep.value === 1) {
    return 'Appointment Details'
  }

  return 'Confirm Appointment'

})


const canContinueBooking = computed(() => {

  if (bookingStep.value === 0) {

    return (
      bookingForm.appointment_date &&
      bookingForm.appointment_time
    )

  }

  return true

})


const fetchDoctor = async () => {

  if (!route.query.doctor) {
    return
  }

  try {

    doctor.value = await call(
      'docbook.api.doctor.get_doctor_by_user',
      {
        user_name: route.query.doctor
      }
    )


  } catch (error) {

    console.error(
      'Failed to fetch doctor:',
      error
    )

  }

}


onMounted(() => {

  fetchDoctor()

})


function openBookingDialog() {

  bookingStep.value = 0

  bookingForm.appointment_date = ''

  bookingForm.appointment_time = ''

  bookingForm.reason = ''

  showBookingDialog.value = true

}


function nextBookingStep() {

  if (bookingStep.value < 2) {

    bookingStep.value += 1

  }

}


async function confirmBooking(close) {

  if (bookingLoading.value) {
    return
  }

  bookingLoading.value = true

  try {

    const response = await call(
      "docbook.api.appointment.create_appointment",
      {
        doctor: doctor.value.user,

        patient: auth.user.email,

        appointment_date:
          bookingForm.appointment_date,

        appointment_time:
          bookingForm.appointment_time,

        reason:
          bookingForm.reason
      }
    )

    close()

    toast.success('Appointment created successfully')

    router.push('/my-appointments')

  } catch (error) {

    console.error(
      'Failed to create appointment:',
      error
    )

    toast.error("Failed to create appointment")

  } finally {

    bookingLoading.value = false

  }

}

</script>


<style scoped>

.date-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
}

.booking-dialog-content {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.dialog-icon {
  display: flex;
  align-items: center;
  justify-content: center;

  width: 46px;
  height: 46px;

  flex-shrink: 0;

  border-radius: 14px;

  background: #eff6ff;

  font-size: 21px;
}

.booking-dialog-content h3 {
  margin: 0;

  color: #0f172a;

  font-size: 15px;

  font-weight: 650;

  line-height: 1.4;
}

.booking-dialog-content p {
  margin: 7px 0 0;

  color: #64748b;

  font-size: 13px;

  line-height: 1.5;
}


/* =========================================
   BOOKING DIALOG - SHARED CONTENT
========================================= */

.booking-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 4px 0 26px;
  width: 100%;
}

.progress-item {
  display: block;
  flex: 1;
  height: 5px;
  border-radius: 999px;
  background: #e2e8f0;
  transition: background 0.25s ease, transform 0.25s ease;
}

.progress-item.active {
  background: linear-gradient(90deg, #2563eb, #14b8a6);
}

.booking-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
  min-width: 0;
  padding: 2px 0 8px;
  color: #0f172a;
  animation: bookingFadeIn 0.25s ease;
}

@keyframes bookingFadeIn {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* =========================================
   DOCTOR SUMMARY
========================================= */

.booking-doctor {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 17px 18px;
  border: 1px solid #dbeafe;
  border-radius: 16px;
  background: linear-gradient(135deg, #eff6ff, #f0fdfa);
}

.booking-doctor > div {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}

.booking-doctor span {
  color: #64748b;
  font-size: 10px;
  font-weight: 750;
  letter-spacing: 1.3px;
}

.booking-doctor strong {
  color: #0f172a;
  font-size: 16px;
  font-weight: 750;
  overflow-wrap: anywhere;
}

/* =========================================
   FORM GRID AND FIELDS
========================================= */

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 9px;
  min-width: 0;
}

.form-group label {
  color: #334155;
  font-size: 13px;
  font-weight: 700;
}

.form-group input,
.form-group textarea {
  box-sizing: border-box;
  width: 100%;
  min-width: 0;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  outline: none;
  background: #fff;
  color: #0f172a;
  font-family: inherit;
  font-size: 14px;
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    background 0.2s ease;
}

.form-group input {
  min-height: 48px;
  padding: 0 13px;
}

.form-group input[type="date"],
.form-group input[type="time"] {
  display: block;
  appearance: auto;
  -webkit-appearance: auto;
}

.form-group textarea {
  min-height: 130px;
  padding: 13px 14px;
  line-height: 1.6;
  resize: vertical;
}

.form-group input:hover,
.form-group textarea:hover {
  border-color: #94a3b8;
}

.form-group input:focus,
.form-group textarea:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.12);
  background: #fff;
}

.form-group input:focus-visible,
.form-group textarea:focus-visible {
  outline: 2px solid transparent;
}

.form-group textarea::placeholder {
  color: #94a3b8;
}

.form-group input:disabled,
.form-group textarea:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

/* =========================================
   CONSULTATION FEE
========================================= */

.fee-preview {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 17px 18px;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: #f8fafc;
}

.fee-preview span {
  color: #64748b;
  font-size: 13px;
  font-weight: 600;
}

.fee-preview strong {
  color: #0f766e;
  font-size: 21px;
  font-weight: 800;
}

/* =========================================
   REASON STEP
========================================= */

.form-heading {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.dialog-icon {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border: 1px solid #dbeafe;
  border-radius: 15px;
  background: #eff6ff;
  font-size: 23px;
}

.form-heading h3 {
  margin: 1px 0 6px;
  color: #0f172a;
  font-size: 18px;
  font-weight: 750;
  line-height: 1.4;
}

.form-heading p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.65;
}

/* =========================================
   REVIEW STEP
========================================= */

.booking-review {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 4px 0 8px;
  color: #0f172a;
  text-align: center;
  animation: bookingFadeIn 0.25s ease;
}

.review-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 58px;
  height: 58px;
  margin-bottom: 15px;
  border: 1px solid #a7f3d0;
  border-radius: 50%;
  background: #ecfdf5;
  color: #059669;
  font-size: 27px;
  font-weight: 800;
}

.booking-review > h3 {
  margin: 0;
  font-size: 21px;
  font-weight: 800;
  letter-spacing: -0.4px;
}

.booking-review > p {
  max-width: 350px;
  margin: 8px 0 22px;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.review-card {
  width: 100%;
  box-sizing: border-box;
  overflow: hidden;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: #fff;
  text-align: left;
}

.review-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  padding: 15px 17px;
  border-bottom: 1px solid #f1f5f9;
}

.review-row:last-child {
  border-bottom: none;
}

.review-row span {
  flex-shrink: 0;
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
}

.review-row strong {
  max-width: 65%;
  color: #0f172a;
  font-size: 13px;
  font-weight: 700;
  text-align: right;
  overflow-wrap: anywhere;
}

.total-row {
  align-items: center;
  background: #f0fdfa;
}

.total-row span {
  color: #0f766e;
}

.total-row strong {
  color: #0f766e;
  font-size: 19px;
  font-weight: 800;
}

/* =========================================
   DIALOG ACTIONS
========================================= */

.booking-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
}

.booking-action-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 10px;
}

/* Extra safety for the buttons inside this dialog */
.booking-actions button {
  min-height: 40px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 700;
  transition:
    transform 0.2s ease,
    opacity 0.2s ease;
}

.booking-actions button:not(:disabled):hover {
  transform: translateY(-1px);
}

.booking-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

/* =========================================
   RESPONSIVE BOOKING FORM
========================================= */

@media (max-width: 560px) {
  .booking-progress {
    margin-bottom: 20px;
  }

  .booking-form {
    gap: 19px;
  }

  .form-grid {
    grid-template-columns: 1fr;
    gap: 17px;
  }

  .booking-doctor {
    padding: 14px;
  }

  .booking-doctor strong {
    font-size: 14px;
  }

  .fee-preview {
    padding: 14px;
  }

  .form-heading h3 {
    font-size: 16px;
  }

  .review-row {
    gap: 12px;
    padding: 13px;
  }

  .review-row span {
    font-size: 11px;
  }

  .review-row strong {
    font-size: 12px;
  }

  .booking-actions {
    align-items: stretch;
    flex-wrap: wrap;
  }

  .booking-action-right {
    gap: 8px;
  }
}

@media (max-width: 380px) {
  .booking-action-right {
    width: 100%;
  }

  .booking-action-right > * {
    flex: 1;
  }

  .review-row {
    flex-direction: column;
    gap: 5px;
  }

  .review-row strong {
    max-width: 100%;
    text-align: left;
  }
}


/* =========================================
   PAGE
========================================= */

.doctor-page {
  position: relative;

  min-height: 100vh;

  overflow: hidden;

  padding: 40px 24px;

  background:
    radial-gradient(
      circle at 10% 10%,
      rgba(37, 99, 235, 0.08),
      transparent 30%
    ),
    radial-gradient(
      circle at 90% 90%,
      rgba(20, 184, 166, 0.08),
      transparent 30%
    ),
    #f4f7fb;

  color: #0f172a;
}


/* Background Orbs */

.bg-orb {
  position: fixed;

  width: 300px;
  height: 300px;

  border-radius: 50%;

  filter: blur(80px);

  pointer-events: none;

  opacity: 0.45;
}

.orb-blue {
  top: -120px;
  left: -100px;

  background: rgba(37, 99, 235, 0.16);
}

.orb-teal {
  right: -100px;
  bottom: -100px;

  background: rgba(20, 184, 166, 0.16);
}


/* =========================================
   CONTAINER
========================================= */

.page-container {
  position: relative;

  z-index: 1;

  width: 100%;
  max-width: 1180px;

  margin: 0 auto;
}


/* =========================================
   HEADER
========================================= */

.page-header {
  display: flex;

  align-items: flex-end;

  justify-content: space-between;

  gap: 20px;

  margin-bottom: 32px;
}

.eyebrow,
.section-eyebrow,
.appointment-label {
  display: block;

  margin-bottom: 7px;

  color: #2563eb;

  font-size: 11px;

  font-weight: 700;

  letter-spacing: 1.5px;
}

.page-header h1 {
  margin: 0;

  font-size: clamp(30px, 4vw, 42px);

  line-height: 1.1;

  font-weight: 750;

  letter-spacing: -1px;
}

.page-header p {
  margin: 10px 0 0;

  color: #64748b;

  font-size: 15px;
}


/* Header Back */

.header-back-button {
  display: flex;

  align-items: center;

  gap: 8px;

  height: 44px;

  padding: 0 17px;

  border: 1px solid rgba(226, 232, 240, 0.9);

  border-radius: 13px;

  background: rgba(255, 255, 255, 0.65);

  backdrop-filter: blur(15px);

  color: #334155;

  font-size: 14px;

  font-weight: 600;

  cursor: pointer;

  transition: 0.2s ease;
}

.header-back-button:hover {
  background: white;

  transform: translateY(-1px);

  box-shadow:
    0 8px 20px rgba(15, 23, 42, 0.06);
}


/* =========================================
   PROFILE LAYOUT
========================================= */

.profile-layout {
  display: grid;

  grid-template-columns:
    minmax(0, 1fr)
    340px;

  gap: 24px;

  align-items: start;
}


/* =========================================
   PROFILE CARD
========================================= */

.profile-card {
  overflow: hidden;

  border: 1px solid rgba(255, 255, 255, 0.8);

  border-radius: 28px;

  background:
    rgba(255, 255, 255, 0.67);

  backdrop-filter: blur(25px);
  -webkit-backdrop-filter: blur(25px);

  box-shadow:
    0 25px 70px rgba(15, 23, 42, 0.08);
}


/* =========================================
   PROFILE HERO
========================================= */

.profile-hero {
  display: flex;

  align-items: center;

  gap: 22px;

  padding: 32px;

  border-bottom:
    1px solid rgba(226, 232, 240, 0.65);
}

.doctor-avatar-wrapper {
  position: relative;

  flex-shrink: 0;
}

.doctor-avatar {
  width: 94px;
  height: 94px;

  display: flex;

  align-items: center;
  justify-content: center;

  border-radius: 27px;

  background:
    linear-gradient(
      135deg,
      #2563eb,
      #14b8a6
    );

  color: white;

  font-size: 38px;

  font-weight: 750;

  box-shadow:
    0 14px 30px rgba(37, 99, 235, 0.25);
}

.online-dot {
  position: absolute;

  right: -3px;
  bottom: -3px;

  width: 20px;
  height: 20px;

  border: 4px solid white;

  border-radius: 50%;

  background: #10b981;
}

.doctor-main-info {
  min-width: 0;
}

.name-row {
  display: flex;

  align-items: center;

  gap: 10px;

  flex-wrap: wrap;
}

.name-row h2 {
  margin: 0;

  color: #0f172a;

  font-size: clamp(24px, 3vw, 32px);

  line-height: 1.2;

  font-weight: 750;

  letter-spacing: -0.7px;
}

.verified-badge {
  display: inline-flex;

  align-items: center;

  gap: 5px;

  padding: 5px 10px;

  border-radius: 999px;

  background: rgba(16, 185, 129, 0.1);

  color: #047857;

  font-size: 11px;

  font-weight: 700;
}

.doctor-title {
  margin: 6px 0 3px;

  color: #334155;

  font-size: 15px;

  font-weight: 600;
}

.doctor-email {
  margin: 0;

  overflow: hidden;

  color: #64748b;

  font-size: 13px;

  text-overflow: ellipsis;

  white-space: nowrap;
}


/* =========================================
   RATING
========================================= */

.rating-section {
  display: flex;

  align-items: center;

  justify-content: space-between;

  gap: 30px;

  padding: 24px 32px;

  border-bottom:
    1px solid rgba(226, 232, 240, 0.65);
}

.rating-main {
  display: flex;

  align-items: center;

  gap: 14px;
}

.rating-star {
  width: 52px;
  height: 52px;

  display: flex;

  align-items: center;
  justify-content: center;

  border-radius: 16px;

  background: rgba(245, 158, 11, 0.1);

  color: #f59e0b;

  font-size: 27px;
}

.rating-number {
  color: #0f172a;

  font-size: 24px;

  font-weight: 750;
}

.rating-number span {
  color: #94a3b8;

  font-size: 13px;

  font-weight: 500;
}

.rating-main p {
  margin: 2px 0 0;

  color: #64748b;

  font-size: 12px;
}


/* Rating Bars */

.rating-bars {
  width: 190px;
}

.rating-bar-row {
  display: flex;

  align-items: center;

  gap: 8px;

  margin: 5px 0;

  color: #94a3b8;

  font-size: 10px;
}

.rating-bar {
  flex: 1;

  height: 5px;

  overflow: hidden;

  border-radius: 99px;

  background: #e2e8f0;
}

.rating-fill {
  height: 100%;

  border-radius: inherit;

  background: #f59e0b;
}

.rating-fill.small {
  width: 18%;
}

.rating-fill.smaller {
  width: 7%;
}


/* =========================================
   SECTION
========================================= */

.section {
  padding: 30px 32px;
}

.section-heading {
  margin-bottom: 18px;
}

.section-heading h3 {
  margin: 0;

  font-size: 20px;

  font-weight: 700;
}

.section-eyebrow {
  margin-bottom: 4px;

  color: #64748b;

  font-size: 10px;
}


/* =========================================
   INFO GRID
========================================= */

.info-grid {
  display: grid;

  grid-template-columns:
    repeat(2, minmax(0, 1fr));

  gap: 14px;
}

.info-card {
  display: flex;

  align-items: center;

  gap: 14px;

  min-width: 0;

  padding: 17px;

  border: 1px solid rgba(226, 232, 240, 0.75);

  border-radius: 18px;

  background: rgba(255, 255, 255, 0.48);

  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    background 0.2s ease;
}

.info-card:hover {
  transform: translateY(-2px);

  background: rgba(255, 255, 255, 0.8);

  box-shadow:
    0 10px 25px rgba(15, 23, 42, 0.05);
}

.info-icon {
  width: 43px;
  height: 43px;

  display: flex;

  align-items: center;
  justify-content: center;

  flex-shrink: 0;

  border-radius: 13px;

  font-size: 17px;

  font-weight: 700;
}

.info-icon.blue {
  background: rgba(37, 99, 235, 0.1);

  color: #2563eb;
}

.info-icon.teal {
  background: rgba(20, 184, 166, 0.1);

  color: #0f766e;
}

.info-icon.purple {
  background: rgba(139, 92, 246, 0.1);

  color: #7c3aed;
}

.info-icon.green {
  background: rgba(16, 185, 129, 0.1);

  color: #059669;
}

.info-content {
  display: flex;

  flex-direction: column;

  gap: 4px;

  min-width: 0;
}

.info-content span {
  color: #64748b;

  font-size: 11px;
}

.info-content strong {
  overflow: hidden;

  color: #0f172a;

  font-size: 15px;

  font-weight: 650;

  text-overflow: ellipsis;

  white-space: nowrap;
}

.info-content small {
  color: #64748b;

  font-size: 11px;

  font-weight: 500;
}

.email-value {
  font-size: 13px !important;
}


/* =========================================
   ACCOUNT
========================================= */

.account-section {
  padding: 20px 32px 28px;

  border-top:
    1px solid rgba(226, 232, 240, 0.65);
}

.account-row {
  display: grid;

  grid-template-columns: 1fr 1fr;

  gap: 20px;
}

.account-row div {
  min-width: 0;
}

.account-row span {
  display: block;

  margin-bottom: 5px;

  color: #94a3b8;

  font-size: 10px;

  text-transform: uppercase;

  letter-spacing: 0.7px;
}

.account-row strong {
  display: block;

  overflow: hidden;

  color: #475569;

  font-size: 12px;

  font-weight: 600;

  text-overflow: ellipsis;

  white-space: nowrap;
}


/* =========================================
   APPOINTMENT CARD
========================================= */

.appointment-card {
  position: sticky;

  top: 24px;

  overflow: hidden;

  border-radius: 28px;

  background:
    linear-gradient(
      145deg,
      #0f172a,
      #172554
    );

  color: white;

  box-shadow:
    0 25px 60px rgba(15, 23, 42, 0.2);
}

.appointment-glow {
  position: absolute;

  width: 180px;
  height: 180px;

  top: -70px;
  right: -60px;

  border-radius: 50%;

  background: rgba(20, 184, 166, 0.3);

  filter: blur(30px);
}

.appointment-content {
  position: relative;

  z-index: 1;

  padding: 30px;
}

.appointment-icon {
  width: 55px;
  height: 55px;

  display: flex;

  align-items: center;
  justify-content: center;

  margin-bottom: 22px;

  border-radius: 17px;

  background: rgba(255, 255, 255, 0.1);

  font-size: 25px;
}

.appointment-label {
  color: #5eead4;
}

.appointment-content h2 {
  margin: 0;

  font-size: 26px;

  line-height: 1.2;

  letter-spacing: -0.5px;
}

.appointment-content > p {
  margin: 13px 0 24px;

  color: #cbd5e1;

  font-size: 13px;

  line-height: 1.7;
}

.appointment-fee {
  display: flex;

  align-items: center;

  justify-content: space-between;

  padding: 15px;

  margin-bottom: 15px;

  border:
    1px solid rgba(255, 255, 255, 0.1);

  border-radius: 15px;

  background: rgba(255, 255, 255, 0.06);
}

.appointment-fee span {
  color: #94a3b8;

  font-size: 12px;
}

.appointment-fee strong {
  color: white;

  font-size: 20px;
}

.book-button {
  width: 100%;

  height: 50px;

  display: flex;

  align-items: center;

  justify-content: space-between;

  padding: 0 18px;

  border: none;

  border-radius: 14px;

  background:
    linear-gradient(
      135deg,
      #2563eb,
      #14b8a6
    );

  color: white;

  font-size: 14px;

  font-weight: 700;

  cursor: pointer;

  box-shadow:
    0 10px 25px rgba(20, 184, 166, 0.2);

  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease;
}

.book-button:hover {
  transform: translateY(-2px);

  box-shadow:
    0 15px 30px rgba(20, 184, 166, 0.3);
}

.book-button span {
  font-size: 20px;
}

.secure-text {
  text-align: center;

  margin: 16px 0 0 !important;

  color: #94a3b8 !important;

  font-size: 10px !important;
}


/* =========================================
   EMPTY STATE
========================================= */

.empty-card,
.loading-card {
  display: flex;

  flex-direction: column;

  align-items: center;

  justify-content: center;

  min-height: 400px;

  padding: 40px;

  text-align: center;

  border: 1px solid rgba(255, 255, 255, 0.8);

  border-radius: 28px;

  background: rgba(255, 255, 255, 0.67);

  backdrop-filter: blur(25px);

  box-shadow:
    0 25px 70px rgba(15, 23, 42, 0.08);
}

.empty-icon {
  width: 70px;
  height: 70px;

  display: flex;

  align-items: center;
  justify-content: center;

  margin-bottom: 18px;

  border-radius: 22px;

  background: rgba(37, 99, 235, 0.1);

  font-size: 30px;
}

.empty-card h2,
.loading-card h3 {
  margin: 0;

  color: #0f172a;
}

.empty-card p,
.loading-card p {
  margin: 8px 0 20px;

  color: #64748b;

  font-size: 14px;
}


/* Loading */

.loading-card {
  flex-direction: row;

  gap: 15px;

  text-align: left;
}

.loader {
  width: 32px;
  height: 32px;

  flex-shrink: 0;

  border: 3px solid #dbeafe;

  border-top-color: #2563eb;

  border-radius: 50%;

  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}


/* =========================================
   BUTTON
========================================= */

.primary-button {
  height: 46px;

  padding: 0 20px;

  border: none;

  border-radius: 13px;

  background: #2563eb;

  color: white;

  font-size: 14px;

  font-weight: 650;

  cursor: pointer;
}

.primary-button:hover {
  background: #1d4ed8;
}


/* =========================================
   TABLET
========================================= */

@media (max-width: 950px) {

  .profile-layout {
    grid-template-columns: 1fr;
  }

  .appointment-card {
    position: relative;

    top: auto;
  }

}


/* =========================================
   MOBILE
========================================= */

@media (max-width: 640px) {

  .doctor-page {
    padding: 24px 14px;
  }


  .page-header {
    align-items: flex-start;

    flex-direction: column;

    margin-bottom: 22px;
  }

  .page-header h1 {
    font-size: 30px;
  }

  .header-back-button {
    width: 100%;

    justify-content: center;
  }


  .profile-card {
    border-radius: 22px;
  }


  .profile-hero {
    align-items: flex-start;

    gap: 16px;

    padding: 22px;
  }

  .doctor-avatar {
    width: 68px;
    height: 68px;

    border-radius: 19px;

    font-size: 28px;
  }

  .online-dot {
    width: 16px;
    height: 16px;

    border-width: 3px;
  }

  .name-row h2 {
    font-size: 22px;
  }

  .doctor-title {
    font-size: 13px;
  }

  .doctor-email {
    max-width: 200px;

    font-size: 11px;
  }


  .rating-section {
    align-items: flex-start;

    flex-direction: column;

    gap: 18px;

    padding: 20px 22px;
  }

  .rating-bars {
    width: 100%;
  }


  .section {
    padding: 24px 22px;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }


  .account-section {
    padding: 18px 22px 24px;
  }

  .account-row {
    grid-template-columns: 1fr;

    gap: 14px;
  }


  .appointment-card {
    border-radius: 22px;
  }

  .appointment-content {
    padding: 24px;
  }

  .appointment-content h2 {
    font-size: 23px;
  }


  .empty-card,
  .loading-card {
    min-height: 330px;

    padding: 25px;

    border-radius: 22px;
  }

  .loading-card {
    flex-direction: column;

    text-align: center;
  }

}


/* =========================================
   SMALL MOBILE
========================================= */

@media (max-width: 400px) {

  .doctor-page {
    padding: 18px 10px;
  }

  .profile-hero {
    padding: 18px;
  }

  .doctor-avatar {
    width: 58px;
    height: 58px;

    font-size: 24px;
  }

  .name-row h2 {
    font-size: 19px;
  }

  .verified-badge {
    font-size: 9px;

    padding: 4px 7px;
  }

  .section,
  .rating-section {
    padding-left: 18px;
    padding-right: 18px;
  }

}

</style>