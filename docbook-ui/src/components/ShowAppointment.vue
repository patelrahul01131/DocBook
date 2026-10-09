<script setup>
import { call } from '../api'
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const appointment = ref(null)
const loading = ref(false)
const error = ref(null)

async function fetchAppointment() {
  loading.value = true
  error.value = null

  try {
    const res = await call(
      'docbook.api.appointment.show_appointment',
      {
        appointment_id: route.params.id
      }
    )

    console.log(res)

    appointment.value = res
  } catch (err) {
    console.error(err)
    error.value = 'Unable to load appointment details.'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchAppointment()
})
</script>

<template>
  <div class="appointment-page">

    <!-- Loading -->
    <div v-if="loading" class="loading-container">
      <div class="loader"></div>
      <p>Loading appointment...</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="error-card">
      <div class="error-icon">!</div>

      <div>
        <h2>Unable to load appointment</h2>
        <p>{{ error }}</p>
      </div>
    </div>

    <!-- Appointment -->
    <div v-else-if="appointment" class="appointment-container">

      <!-- Header -->
      <div class="page-header">
        <div>

          <button
            class="header-back-button mb-4"
            @click="$router.back()"
          >
            <span>←</span>
            Back
        </button>

          <p class="page-label">Appointment Details</p>

          <h1>
            Appointment
            <span>#{{ appointment[0].slot }}</span>
          </h1>

          <p class="created-text">
            Created on {{ appointment[0].created_at }}
          </p>

        </div>

        <div
          class="status-badge"
          :class="appointment.status?.toLowerCase()"
        >
          <span class="status-dot"></span>
          {{ appointment.status }}
        </div>
      </div>

      <!-- Main Grid -->
      <div class="content-grid">

        <!-- Left -->
        <div class="main-content">

          <!-- Appointment Information -->
          <section class="card">
            <div class="card-header">
              <div>
                <p class="section-label">Schedule</p>
                <h2>Appointment Information</h2>
              </div>

              <div class="calendar-icon">
                📅
              </div>
            </div>

            <div class="info-grid">

              <div class="info-item">
                <span class="info-label">Date</span>
                <span class="info-value">
                  {{ appointment[0].appointment_date }}
                </span>
              </div>

              <div class="info-item">
                <span class="info-label">Time</span>
                <span class="info-value">
                  {{ appointment[0].appointment_time }}
                </span>
              </div>

              <div class="info-item">
                <span class="info-label">Slot</span>
                <span class="info-value">
                  {{ appointment[0].slot }}
                </span>
              </div>

              <div class="info-item">
                <span class="info-label">Appointment ID</span>
                <span class="info-value">
                  {{ appointment[0].name }}
                </span>
              </div>

            </div>
          </section>


          <!-- Doctor & Patient -->
          <section class="people-grid">

            <!-- Doctor -->
            <div class="person-card">
              <div class="person-icon doctor-icon">
                👨‍⚕️
              </div>

              <div class="person-content">
                <span class="info-label">Doctor</span>

                <h3>
                  {{ appointment[0].doctor }}
                </h3>

                <p>Assigned Doctor</p>
              </div>
            </div>


            <!-- Patient -->
            <div class="person-card">
              <div class="person-icon patient-icon">
                👤
              </div>

              <div class="person-content">
                <span class="info-label">Patient</span>

                <h3>
                  {{ appointment[0].patient }}
                </h3>

                <p>Registered Patient</p>
              </div>
            </div>

          </section>


          <!-- Reason -->
          <section class="card">
            <div class="card-header">
              <div>
                <p class="section-label">Consultation</p>
                <h2>Reason for Visit</h2>
              </div>
            </div>

            <div class="reason-box">
              <p v-if="appointment[0].reason">
                {{ appointment[0].reason }}
              </p>

              <p v-else class="empty-text">
                No reason provided for this appointment.
              </p>
            </div>
          </section>

        </div>


        <!-- Right Sidebar -->
        <aside class="sidebar">

          <!-- Payment -->
          <section class="card payment-card">

            <div class="card-header">
              <div>
                <p class="section-label">Payment</p>
                <h2>Consultation Fee</h2>
              </div>

              <div class="payment-icon">
                ₹
              </div>
            </div>

            <div class="price">
              ₹{{ appointment[0].consultation_fee }}
            </div>

            <div
              class="payment-status"
              :class="appointment[0].payment_status?.toLowerCase()"
            >
              {{ appointment[0].payment_status }}
            </div>

          </section>


          <!-- Details -->
          <section class="card">

            <div class="card-header">
              <div>
                <p class="section-label">Information</p>
                <h2>Details</h2>
              </div>
            </div>

            <div class="details-list">

              <div class="detail-row">
                <span>Status</span>
                <strong>{{ appointment[0].status }}</strong>
              </div>

              <div class="detail-row">
                <span>Payment</span>
                <strong>{{ appointment[0].payment_status }}</strong>
              </div>

              <div class="detail-row">
                <span>Slot</span>
                <strong>{{ appointment[0].slot }}</strong>
              </div>

              <div class="detail-row">
                <span>Created</span>
                <strong>{{ appointment[0].created_at }}</strong>
              </div>

            </div>

          </section>

        </aside>

      </div>

    </div>

  </div>
</template>


<style scoped>

* {
  box-sizing: border-box;
}

.appointment-page {
  min-height: 100vh;
  background: #f8fafc;
  padding: 32px;
  color: #172033;
}

.appointment-container {
  max-width: 1200px;
  margin: 0 auto;
}


/* ---------------- HEADER ---------------- */

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
  margin-bottom: 28px;
}


.page-label,
.section-label {
  margin: 0 0 5px;
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.page-header h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: #0f172a;
}

.page-header h1 span {
  color: #64748b;
  font-weight: 500;
}

.created-text {
  margin: 7px 0 0;
  color: #94a3b8;
  font-size: 13px;
}


/* ---------------- STATUS ---------------- */

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 999px;
  background: #fef3c7;
  color: #92400e;
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
}

.status-badge.pending {
  background: #fef3c7;
  color: #92400e;
}

.status-badge.confirmed {
  background: #dcfce7;
  color: #166534;
}

.status-badge.completed {
  background: #dbeafe;
  color: #1d4ed8;
}

.status-badge.cancelled {
  background: #fee2e2;
  color: #b91c1c;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
}


/* ---------------- GRID ---------------- */

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 330px;
  gap: 24px;
}

.main-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 20px;
}


/* ---------------- CARD ---------------- */

.card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 24px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 22px;
}

.card-header h2 {
  margin: 0;
  font-size: 17px;
  font-weight: 650;
  color: #0f172a;
}

.calendar-icon,
.payment-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: #f1f5f9;
  font-size: 18px;
}


/* ---------------- INFO ---------------- */

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  border-top: 1px solid #f1f5f9;
}

.info-item {
  padding: 18px 10px;
  border-bottom: 1px solid #f1f5f9;
}

.info-item:nth-child(odd) {
  padding-left: 0;
  border-right: 1px solid #f1f5f9;
}

.info-item:nth-child(even) {
  padding-left: 20px;
}

.info-label {
  display: block;
  margin-bottom: 6px;
  color: #94a3b8;
  font-size: 12px;
  font-weight: 500;
}

.info-value {
  color: #334155;
  font-size: 14px;
  font-weight: 600;
}


/* ---------------- PEOPLE ---------------- */

.people-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
}

.person-card {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 20px;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
}

.person-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 48px;
  height: 48px;
  border-radius: 12px;
  font-size: 22px;
}

.doctor-icon {
  background: #eff6ff;
}

.patient-icon {
  background: #f0fdf4;
}

.person-content {
  min-width: 0;
}

.person-content h3 {
  margin: 0;
  overflow: hidden;
  color: #1e293b;
  font-size: 14px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.person-content p {
  margin: 4px 0 0;
  color: #94a3b8;
  font-size: 12px;
}


/* ---------------- REASON ---------------- */

.reason-box {
  min-height: 90px;
  padding: 16px;
  border-radius: 10px;
  background: #f8fafc;
}

.reason-box p {
  margin: 0;
  color: #475569;
  font-size: 14px;
  line-height: 1.6;
}

.empty-text {
  color: #94a3b8 !important;
}


/* ---------------- PAYMENT ---------------- */

.payment-card {
  position: relative;
}

.price {
  margin: 5px 0 14px;
  color: #0f172a;
  font-size: 32px;
  font-weight: 700;
}

.payment-status {
  display: inline-block;
  padding: 5px 10px;
  border-radius: 6px;
  background: #fef3c7;
  color: #92400e;
  font-size: 12px;
  font-weight: 600;
}

.payment-status.paid {
  background: #dcfce7;
  color: #166534;
}

.payment-status.pending {
  background: #fef3c7;
  color: #92400e;
}


/* ---------------- DETAILS ---------------- */

.details-list {
  display: flex;
  flex-direction: column;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  gap: 15px;
  padding: 13px 0;
  border-bottom: 1px solid #f1f5f9;
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-row span {
  color: #64748b;
  font-size: 13px;
}

.detail-row strong {
  max-width: 180px;
  overflow: hidden;
  color: #334155;
  font-size: 13px;
  font-weight: 600;
  text-align: right;
  text-overflow: ellipsis;
}


/* ---------------- LOADING ---------------- */

.loading-container {
  display: flex;
  min-height: 300px;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 12px;
  color: #64748b;
}

.loader {
  width: 28px;
  height: 28px;
  border: 3px solid #e2e8f0;
  border-top-color: #64748b;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.loading-container p {
  margin: 0;
  font-size: 14px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}


/* ---------------- ERROR ---------------- */

.error-card {
  display: flex;
  max-width: 600px;
  margin: 80px auto;
  align-items: center;
  gap: 15px;
  padding: 22px;
  background: white;
  border: 1px solid #fecaca;
  border-radius: 14px;
}

.error-icon {
  display: flex;
  width: 40px;
  height: 40px;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: 50%;
  background: #fee2e2;
  color: #b91c1c;
  font-weight: 700;
}

.error-card h2 {
  margin: 0;
  color: #991b1b;
  font-size: 16px;
}

.error-card p {
  margin: 5px 0 0;
  color: #64748b;
  font-size: 13px;
}


/* ---------------- RESPONSIVE ---------------- */

@media (max-width: 900px) {
  .content-grid {
    grid-template-columns: 1fr;
  }

  .sidebar {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 650px) {
  .appointment-page {
    padding: 18px;
  }

  .page-header {
    flex-direction: column;
  }

  .page-header h1 {
    font-size: 23px;
  }

  .people-grid {
    grid-template-columns: 1fr;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }

  .info-item:nth-child(odd) {
    padding-left: 0;
    border-right: none;
  }

  .info-item:nth-child(even) {
    padding-left: 0;
  }

  .sidebar {
    display: flex;
  }
}

</style>