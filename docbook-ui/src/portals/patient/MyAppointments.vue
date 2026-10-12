<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { Button } from "frappe-ui";
import { toast } from "frappe-ui";
import { call } from "../../api";
import { useAuthStore } from "../../stores/auth";

const auth = useAuthStore();
const router = useRouter();

const appointments = ref([]);
const loading = ref(false);
const error = ref(null);
const activeTab = ref("all");
const searchQuery = ref("");

// Reschedule Modal
const showRescheduleModal = ref(false);
const selectedAppt = ref(null);
const rescheduleDate = ref("");
const rescheduleTime = ref("");
const rescheduleReason = ref("");
const availableSlots = ref([]);
const loadingSlots = ref(false);
const rescheduling = ref(false);
const rescheduleError = ref(null);

const cancelling = ref(null);
const deleting = ref(null);

// Review Modal
const showReviewModal = ref(false);
const reviewAppt = ref(null);
const reviewRating = ref(5);
const reviewFeedback = ref("");
const submittingReview = ref(false);
const myReviews = ref({});
const existingReviewView = ref(null);

const tabs = [
  { key: "all", label: "All" },
  { key: "upcoming", label: "Upcoming" },
  { key: "completed", label: "Completed" },
  { key: "cancelled", label: "Cancelled" },
];

async function fetchAppointments() {
  loading.value = true;
  error.value = null;

  try {
    const res = await call("docbook.api.appointment.list_appointment", {
      patient: auth.user?.email,
    });
    appointments.value = Array.isArray(res) ? res : [];
    fetchMyReviews();
  } catch (err) {
    console.error(err);
    error.value = err.message || "Unable to load your appointments.";
  } finally {
    loading.value = false;
  }
}

function isUpcoming(appointment) {
  if (!appointment.appointment_date) return false;
  if (['Completed', 'Cancelled'].includes(appointment.status)) return false;
  const appointmentDate = new Date(
    `${appointment.appointment_date}T${appointment.appointment_time || "00:00:00"}`
  );
  return appointmentDate >= new Date();
}

const filteredAppointments = computed(() => {
  let list = appointments.value;

  if (activeTab.value === "upcoming") {
    list = list.filter(a => isUpcoming(a));
  } else if (activeTab.value === "completed") {
    list = list.filter(a => a.status === "Completed");
  } else if (activeTab.value === "cancelled") {
    list = list.filter(a => a.status === "Cancelled");
  }

  const q = searchQuery.value.trim().toLowerCase();
  if (q) {
    list = list.filter(a =>
      (a.doctor_name || a.doctor || "").toLowerCase().includes(q) ||
      (a.doctor_specialty || "").toLowerCase().includes(q) ||
      (a.reason || "").toLowerCase().includes(q) ||
      (a.name || "").toLowerCase().includes(q)
    );
  }

  return list;
});

function tabCount(key) {
  if (key === "all") return appointments.value.length;
  if (key === "upcoming") return appointments.value.filter(a => isUpcoming(a)).length;
  if (key === "completed") return appointments.value.filter(a => a.status === "Completed").length;
  if (key === "cancelled") return appointments.value.filter(a => a.status === "Cancelled").length;
  return 0;
}

// Reschedule
async function openReschedule(appt) {
  selectedAppt.value = appt;
  rescheduleDate.value = appt.appointment_date || "";
  rescheduleTime.value = appt.appointment_time || "";
  rescheduleReason.value = appt.reason || "";
  showRescheduleModal.value = true;
  await fetchAvailableSlots();
}

async function fetchAvailableSlots() {
  if (!rescheduleDate.value || !selectedAppt.value?.doctor) return;
  loadingSlots.value = true;
  rescheduleError.value = null;
  try {
    const slots = await call("docbook.api.appointment.get_available_slots", {
      doctor: selectedAppt.value.doctor,
      date: rescheduleDate.value,
    });
    availableSlots.value = Array.isArray(slots) ? slots : [];
  } catch (err) {
    availableSlots.value = [];
    rescheduleError.value = err.message || "Unable to load slots.";
  } finally {
    loadingSlots.value = false;
  }
}

async function submitReschedule() {
  if (!rescheduleDate.value || !rescheduleTime.value) {
    rescheduleError.value = "Please select both date and time slot.";
    return;
  }
  rescheduling.value = true;
  rescheduleError.value = null;

  try {
    await call("docbook.api.appointment.update_appointment", {
      appointment_id: selectedAppt.value.name,
      appointment_date: rescheduleDate.value,
      appointment_time: rescheduleTime.value,
      reason: rescheduleReason.value,
    });
    showRescheduleModal.value = false;
    await fetchAppointments();
  } catch (err) {
    rescheduleError.value = err.message || "Failed to reschedule appointment.";
  } finally {
    rescheduling.value = false;
  }
}

async function cancelAppointment(appt) {
  if (!confirm(`Are you sure you want to cancel appointment #${appt.name}?`)) return;
  cancelling.value = appt.name;
  try {
    await call("docbook.api.appointment.cancel_appointment", {
      appointment_id: appt.name,
    });
    await fetchAppointments();
  } catch (err) {
    alert(err.message || "Failed to cancel appointment.");
  } finally {
    cancelling.value = null;
  }
}

async function deleteAppointment(appt) {
  if (!confirm(`Are you sure you want to delete appointment #${appt.name}?`)) return;
  deleting.value = appt.name;
  try {
    await call("docbook.api.appointment.delete_appointment", {
      appointment_id: appt.name,
    });
    await fetchAppointments();
  } catch (err) {
    alert(err.message || "Failed to delete appointment.");
  } finally {
    deleting.value = null;
  }
}

// ---------------------------------------------------------------------------
// Reviews
// ---------------------------------------------------------------------------
async function fetchMyReviews() {
  try {
    const res = await call("docbook.api.review.get_my_reviews");
    myReviews.value = res && typeof res === "object" ? res : {};
  } catch (err) {
    console.error("Failed to load reviews:", err);
    myReviews.value = {};
  }
}

function hasReview(appt) {
  return !!myReviews.value[appt.name];
}

function openReview(appt) {
  const existing = myReviews.value[appt.name];
  if (existing) {
    existingReviewView.value = existing;
    reviewAppt.value = appt;
    reviewRating.value = existing.rating || 5;
    reviewFeedback.value = existing.feedback || "";
  } else {
    existingReviewView.value = null;
    reviewAppt.value = appt;
    reviewRating.value = 5;
    reviewFeedback.value = "";
  }
  showReviewModal.value = true;
}

function closeReview() {
  showReviewModal.value = false;
  reviewAppt.value = null;
  existingReviewView.value = null;
}

function setRating(n) {
  if (existingReviewView.value) return;
  reviewRating.value = n;
}

async function submitReview() {
  if (!reviewAppt.value || submittingReview.value) return;
  submittingReview.value = true;
  try {
    await call("docbook.api.review.submit_review", {
      appointment_id: reviewAppt.value.name,
      rating: reviewRating.value,
      feedback: reviewFeedback.value,
    });
    toast.success("Thanks! Your review has been submitted.");
    closeReview();
    await fetchMyReviews();
  } catch (err) {
    alert(err.message || "Failed to submit review.");
  } finally {
    submittingReview.value = false;
  }
}

function formatDate(date) {
  if (!date) return "-";
  return new Date(`${date}T00:00:00`).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function formatTime(t) {
  if (!t) return "-";
  const [h, m] = t.split(":");
  const hour = parseInt(h, 10);
  const ampm = hour >= 12 ? "PM" : "AM";
  const displayHour = hour % 12 || 12;
  return `${displayHour}:${m} ${ampm}`;
}

function formatDoctorName(doctor) {
  if (!doctor) return "Doctor";
  return doctor.includes("@") ? doctor.split("@")[0] : doctor;
}

function getDoctorInitial(name) {
  if (!name) return "D";
  return name.charAt(0).toUpperCase();
}

function goToDoctors() {
  router.push("/home");
}

function redirectLogin() {
  router.push("/login");
}

onMounted(() => {
  fetchAppointments();
});
</script>

<template>
  <div class="appointments-page">
    <div class="page-container">

      <!-- Header -->
      <section class="page-header">
        <div>
          <div class="eyebrow">
            <span class="lucide-calendar"></span>
            PATIENT PORTAL
          </div>
          <h1>My Appointments<span>.</span></h1>
          <p>View, reschedule, and manage all your healthcare visits.</p>
        </div>

        <div class="header-actions">
          <Button
            label="Book New Visit"
            icon-left="lucide-calendar-plus"
            @click="goToDoctors"
          />
          <Button
            label="Refresh"
            icon-left="lucide-refresh-cw"
            :loading="loading"
            @click="fetchAppointments"
          />
        </div>
      </section>

      <!-- Auth Guard -->
      <div v-if="!auth.isLoggedIn" class="state-card">
        <h3>Sign in to view your appointments</h3>
        <p>Please log in to manage your appointments and health records.</p>
        <button class="primary-btn mt-3" @click="redirectLogin">Login Now →</button>
      </div>

      <!-- Loading -->
      <div v-else-if="loading" class="state-card">
        <div class="loader"></div>
        <p>Loading your appointments...</p>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="state-card error-state">
        <div class="state-icon">!</div>
        <h3>Unable to load appointments</h3>
        <p>{{ error }}</p>
        <button class="retry-btn mt-3" @click="fetchAppointments">Try Again</button>
      </div>

      <!-- Main Appointments View -->
      <div v-else>

        <!-- Stats Grid -->
        <section class="stats-grid">
          <div class="stat-card">
            <div class="stat-icon blue">
              <span class="lucide-calendar-days"></span>
            </div>
            <div>
              <span>Total Bookings</span>
              <strong>{{ appointments.length }}</strong>
            </div>
          </div>

          <div class="stat-card">
            <div class="stat-icon teal">
              <span class="lucide-calendar-check"></span>
            </div>
            <div>
              <span>Upcoming Visits</span>
              <strong>{{ tabCount('upcoming') }}</strong>
            </div>
          </div>

          <div class="stat-card">
            <div class="stat-icon purple">
              <span class="lucide-check-circle-2"></span>
            </div>
            <div>
              <span>Completed</span>
              <strong>{{ tabCount('completed') }}</strong>
            </div>
          </div>
        </section>

        <!-- Search & Filter Controls -->
        <div class="controls-row">
          <div class="search-box">
            <span class="lucide-search search-icon"></span>
            <input
              v-model="searchQuery"
              type="text"
              class="search-input"
              placeholder="Search by doctor, specialty, reason, or appointment ID..."
            />
            <button v-if="searchQuery" class="clear-btn" @click="searchQuery = ''">✕</button>
          </div>

          <div class="filter-tabs">
            <button
              v-for="t in tabs"
              :key="t.key"
              class="tab-btn"
              :class="{ active: activeTab === t.key }"
              @click="activeTab = t.key"
            >
              {{ t.label }}
              <span class="tab-badge">{{ tabCount(t.key) }}</span>
            </button>
          </div>
        </div>

        <!-- Empty State -->
        <div v-if="!filteredAppointments.length" class="state-card">
          <div class="empty-icon">
            <span class="lucide-calendar-x"></span>
          </div>
          <h3>No appointments found</h3>
          <p v-if="searchQuery">No appointments match "{{ searchQuery }}".</p>
          <p v-else>You don't have any appointments in the "{{ activeTab }}" view.</p>
          <button class="primary-btn mt-3" @click="goToDoctors">Book an Appointment →</button>
        </div>

        <!-- Appointments List -->
        <div v-else class="appointments-list">
          <article
            v-for="appt in filteredAppointments"
            :key="appt.name"
            class="appointment-card"
          >
            <!-- Top Strip: Doctor & Status -->
            <div class="card-header">
              <div class="doctor-profile">
                <div class="doctor-avatar">
                  {{ getDoctorInitial(appt.doctor_name || appt.doctor) }}
                </div>
                <div>
                  <h3 class="doctor-name">
                    Dr. {{ appt.doctor_name || formatDoctorName(appt.doctor) }}
                  </h3>
                  <p class="specialty-sub">
                    {{ appt.doctor_specialty || "Certified Specialist" }}
                  </p>
                </div>
              </div>

              <div class="header-status">
                <span
                  class="status-pill"
                  :class="`status-${(appt.status || 'pending').toLowerCase()}`"
                >
                  {{ appt.status || 'Pending' }}
                </span>
              </div>
            </div>

            <!-- Schedule & Details Strip -->
            <div class="schedule-strip">
              <div class="strip-item">
                <span class="lucide-calendar"></span>
                <strong>{{ formatDate(appt.appointment_date) }}</strong>
              </div>
              <div class="strip-item">
                <span class="lucide-clock"></span>
                <strong>{{ formatTime(appt.appointment_time) }}</strong>
              </div>
              <div class="strip-item fee">
                <span>Fee: ₹{{ appt.consultation_fee || 0 }}</span>
              </div>
            </div>

            <!-- Reason / Clinical Notes -->
            <div v-if="appt.reason" class="reason-preview">
              <span class="font-semibold text-slate-700">Reason:</span> {{ appt.reason }}
            </div>

            <div v-if="appt.diagnosis" class="diagnosis-preview">
              <span class="font-bold text-teal-800">Dx:</span> {{ appt.diagnosis }}
            </div>

            <!-- Actions Footer -->
            <div class="card-actions">
              <button
                class="btn-action btn-action--view"
                @click="router.push(`/show-appointment/${appt.name}`)"
              >
                <span class="lucide-file-text"></span>
                View Full Details
              </button>

              <!-- Reschedule (if not completed/cancelled) -->
              <button
                v-if="!['Completed', 'Cancelled'].includes(appt.status)"
                class="btn-action btn-action--reschedule"
                @click="openReschedule(appt)"
              >
                <span class="lucide-calendar-clock"></span>
                Reschedule
              </button>

              <!-- Cancel -->
              <button
                v-if="!['Completed', 'Cancelled'].includes(appt.status)"
                class="btn-action btn-action--cancel"
                :disabled="cancelling === appt.name"
                @click="cancelAppointment(appt)"
              >
                ✕ Cancel
              </button>

              <!-- Delete (if cancelled or pending) -->
              <button
                v-if="appt.status !== 'Completed'"
                class="btn-action btn-action--delete"
                :disabled="deleting === appt.name"
                @click="deleteAppointment(appt)"
                title="Delete Appointment"
              >
                🗑️
              </button>

              <!-- Review (completed appointments only) -->
              <button
                v-if="appt.status === 'Completed'"
                class="btn-action btn-action--review"
                :class="{ 'is-reviewed': hasReview(appt) }"
                @click="openReview(appt)"
              >
                <span class="lucide-star"></span>
                {{ hasReview(appt) ? 'Reviewed' : 'Write Review' }}
              </button>
            </div>
          </article>
        </div>

      </div>

    </div>

    <!-- Reschedule Modal -->
    <div v-if="showRescheduleModal" class="modal-backdrop" @click.self="showRescheduleModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <div>
            <h3>Reschedule Appointment #{{ selectedAppt?.name }}</h3>
            <p class="text-xs text-slate-500">
              Dr. {{ selectedAppt?.doctor_name || selectedAppt?.doctor }}
            </p>
          </div>
          <button class="close-btn" @click="showRescheduleModal = false">✕</button>
        </div>

        <div class="modal-body">
          <div v-if="rescheduleError" class="modal-error">
            {{ rescheduleError }}
          </div>

          <!-- Date -->
          <div class="form-group mb-4">
            <label class="form-label">Select Date *</label>
            <input
              v-model="rescheduleDate"
              type="date"
              class="form-input"
              @change="fetchAvailableSlots"
            />
          </div>

          <!-- Time Slots -->
          <div class="form-group mb-4">
            <label class="form-label">Select Time Slot *</label>
            <div v-if="loadingSlots" class="text-xs text-slate-500 py-3 text-center">
              Checking doctor availability...
            </div>
            <div v-else-if="!availableSlots.length" class="empty-slots">
              No available slots on this date. Please pick another date.
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

          <!-- Reason -->
          <div class="form-group">
            <label class="form-label">Reason for Visit / Update Notes</label>
            <textarea
              v-model="rescheduleReason"
              rows="3"
              class="form-textarea"
              placeholder="e.g. Schedule conflict, symptom follow-up..."
            ></textarea>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-cancel" @click="showRescheduleModal = false">Cancel</button>
          <button
            class="btn-submit"
            :disabled="rescheduling || !rescheduleDate || !rescheduleTime"
            @click="submitReschedule"
          >
            {{ rescheduling ? 'Rescheduling...' : 'Confirm Reschedule' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Review Modal -->
    <div v-if="showReviewModal" class="modal-backdrop" @click.self="closeReview">
      <div class="modal-card review-modal">
        <div class="modal-header">
          <div>
            <h3>
              {{ existingReviewView ? 'Your Review' : 'Rate Your Visit' }}
            </h3>
            <p class="text-xs text-slate-500">
              Dr. {{ reviewAppt?.doctor_name || reviewAppt?.doctor }}
            </p>
          </div>
          <button class="close-btn" @click="closeReview">✕</button>
        </div>

        <div class="modal-body">
          <!-- Star Rating -->
          <div class="star-rating">
            <button
              v-for="n in 5"
              :key="n"
              type="button"
              class="star-btn"
              :class="{ active: n <= reviewRating }"
              :disabled="!!existingReviewView"
              @click="setRating(n)"
            >
              ★
            </button>
          </div>
          <p class="rating-caption">
            {{ ['Poor', 'Fair', 'Good', 'Very Good', 'Excellent'][reviewRating - 1] }}
          </p>

          <!-- Feedback -->
          <div class="form-group mt-4">
            <label class="form-label">
              {{ existingReviewView ? 'Feedback' : 'Share your experience (optional)' }}
            </label>
            <textarea
              v-model="reviewFeedback"
              rows="4"
              class="form-textarea"
              :readonly="!!existingReviewView"
              placeholder="How was your consultation? "
            ></textarea>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-cancel" @click="closeReview">Close</button>
          <button
            v-if="!existingReviewView"
            class="btn-submit"
            :disabled="submittingReview || !reviewRating"
            @click="submitReview"
          >
            {{ submittingReview ? 'Submitting...' : 'Submit Review' }}
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.appointments-page {
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
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 28px;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.8);
}

.page-header h1 {
  font-size: clamp(28px, 3.5vw, 38px);
  font-weight: 800;
  letter-spacing: -1.2px;
  margin: 0 0 6px;
  color: #0f172a;
}

.page-header h1 span { color: #0d9488; }
.page-header p { font-size: 14px; color: #64748b; margin: 0; }
.header-actions { display: flex; gap: 10px; }

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 16px;
  padding: 18px 20px;
}

.stat-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}
.stat-icon.blue   { background: rgba(37, 99, 235, 0.12); color: #2563eb; }
.stat-icon.teal   { background: rgba(13, 148, 136, 0.12); color: #0d9488; }
.stat-icon.purple { background: rgba(124, 58, 237, 0.12); color: #7c3aed; }

.stat-card span { font-size: 12px; color: #64748b; font-weight: 600; display: block; }
.stat-card strong { font-size: 24px; font-weight: 800; color: #0f172a; }

/* Controls */
.controls-row {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 24px;
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
  max-width: 480px;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
}
.search-icon { margin-left: 12px; font-size: 16px; color: #94a3b8; }
.search-input {
  flex: 1;
  padding: 10px 12px;
  border: none;
  background: transparent;
  font-size: 13px;
  outline: none;
}
.clear-btn { padding: 6px 12px; background: none; border: none; color: #94a3b8; cursor: pointer; }

.filter-tabs { display: flex; gap: 8px; overflow-x: auto; }
.tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  background: white;
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  transition: all 0.15s;
}
.tab-btn.active {
  background: #0d9488;
  color: white;
  border-color: #0d9488;
}
.tab-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #475569;
}
.tab-btn.active .tab-badge {
  background: rgba(255, 255, 255, 0.25);
  color: white;
}

/* Appointments List */
.appointments-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
}

.appointment-card {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 20px;
  padding: 22px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
  display: flex;
  flex-direction: column;
  gap: 14px;
  transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
}
.appointment-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 32px rgba(15, 23, 42, 0.08);
  border-color: rgba(13, 148, 136, 0.4);
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.doctor-profile {
  display: flex;
  align-items: center;
  gap: 12px;
}

.doctor-avatar {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: linear-gradient(135deg, #0d9488 0%, #2563eb 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  font-weight: 800;
  box-shadow: 0 4px 12px rgba(13, 148, 136, 0.2);
}

.doctor-name {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 2px;
}
.specialty-sub { font-size: 12px; color: #64748b; margin: 0; }

.status-pill {
  font-size: 11px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 999px;
  text-transform: capitalize;
}
.status-pending   { background: #fef3c7; color: #b45309; }
.status-confirmed { background: #d1fae5; color: #047857; }
.status-completed { background: #dbeafe; color: #1e40af; }
.status-cancelled { background: #fee2e2; color: #b91c1c; }

.schedule-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f8fafc;
  padding: 9px 12px;
  border-radius: 10px;
  font-size: 12px;
}
.strip-item { display: flex; align-items: center; gap: 6px; color: #475569; }
.strip-item strong { color: #0f172a; }
.strip-item.fee { font-weight: 700; color: #0d9488; }

.reason-preview {
  font-size: 12px;
  color: #334155;
  background: #f1f5f9;
  padding: 8px 10px;
  border-radius: 8px;
}

.diagnosis-preview {
  font-size: 12px;
  color: #0f766e;
  background: #f0fdfa;
  border: 1px solid #ccfbf1;
  padding: 8px 10px;
  border-radius: 8px;
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid #f1f5f9;
}

.btn-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 7px 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s;
}

.btn-action--view {
  background: #0d9488;
  color: white;
  flex: 1;
}
.btn-action--view:hover { background: #0f766e; }

.btn-action--reschedule {
  background: white;
  border-color: #e2e8f0;
  color: #475569;
}
.btn-action--reschedule:hover { background: #f8fafc; color: #0f172a; }

.btn-action--cancel {
  background: #fef2f2;
  border-color: #fecaca;
  color: #b91c1c;
}
.btn-action--cancel:hover { background: #fee2e2; }

.btn-action--delete {
  background: none;
  border: none;
  color: #94a3b8;
  padding: 6px;
}
.btn-action--delete:hover { color: #ef4444; }

.btn-action--review {
  background: #fffbeb;
  border-color: #fde68a;
  color: #b45309;
}
.btn-action--review:hover { background: #fef3c7; }
.btn-action--review.is-reviewed {
  background: #f0fdfa;
  border-color: #99f6e4;
  color: #0d9488;
}

/* Review modal */
.review-modal .modal-body { text-align: center; }
.star-rating {
  display: flex;
  justify-content: center;
  gap: 6px;
  margin: 6px 0 2px;
}
.star-btn {
  background: none;
  border: none;
  font-size: 34px;
  line-height: 1;
  color: #e2e8f0;
  cursor: pointer;
  transition: color 0.15s, transform 0.1s;
}
.star-btn:hover { transform: scale(1.15); }
.star-btn.active { color: #f59e0b; }
.star-btn:disabled { cursor: default; }
.star-btn:disabled:hover { transform: none; }
.rating-caption {
  font-size: 13px;
  font-weight: 700;
  color: #0d9488;
  margin-top: 2px;
}

/* States */
.state-card {
  padding: 60px 20px;
  text-align: center;
  background: white;
  border-radius: 20px;
  border: 1px dashed #cbd5e1;
}
.empty-icon {
  width: 50px;
  height: 50px;
  border-radius: 14px;
  background: #f0fdfa;
  color: #0d9488;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  margin: 0 auto 12px;
}
.primary-btn {
  padding: 9px 18px;
  border-radius: 10px;
  background: #0d9488;
  color: white;
  font-size: 13px;
  font-weight: 700;
  border: none;
  cursor: pointer;
}
.loader {
  width: 28px;
  height: 28px;
  border: 3px solid #e2e8f0;
  border-top-color: #0d9488;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 10px;
}
@keyframes spin { to { transform: rotate(360deg); } }

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
  max-width: 500px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 24px 64px rgba(15, 23, 42, 0.2);
  overflow: hidden;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  padding: 18px 22px;
  border-bottom: 1px solid #f1f5f9;
}
.modal-header h3 { font-size: 16px; font-weight: 800; color: #0f172a; margin: 0 0 2px; }
.close-btn { background: none; border: none; font-size: 16px; color: #94a3b8; cursor: pointer; }
.modal-body { padding: 18px 22px; overflow-y: auto; flex: 1; }
.modal-error { background: #fef2f2; color: #b91c1c; padding: 8px 12px; border-radius: 8px; font-size: 12px; margin-bottom: 12px; }
.form-label { display: block; font-size: 12px; font-weight: 700; color: #475569; margin-bottom: 6px; }
.form-input, .form-textarea { width: 100%; padding: 9px 12px; border: 1px solid #e2e8f0; border-radius: 10px; font-size: 13px; outline: none; }
.form-input:focus, .form-textarea:focus { border-color: #0d9488; }
.slots-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(85px, 1fr)); gap: 8px; max-height: 160px; overflow-y: auto; }
.slot-btn { padding: 7px 4px; border: 1px solid #e2e8f0; background: white; border-radius: 8px; font-size: 11px; font-weight: 600; cursor: pointer; }
.slot-btn.active { background: #0d9488; color: white; border-color: #0d9488; }
.empty-slots { padding: 12px; background: #f8fafc; border-radius: 8px; font-size: 12px; color: #64748b; text-align: center; }
.modal-footer { padding: 14px 22px; border-top: 1px solid #f1f5f9; display: flex; justify-content: flex-end; gap: 10px; }
.btn-submit { padding: 8px 16px; background: #0d9488; color: white; border: none; border-radius: 10px; font-size: 12px; font-weight: 700; cursor: pointer; }
.btn-cancel { padding: 8px 14px; background: white; border: 1px solid #e2e8f0; border-radius: 10px; font-size: 12px; color: #475569; cursor: pointer; }

@media (max-width: 768px) {
  .appointments-page { padding: 20px 16px; }
  .stats-grid { grid-template-columns: 1fr; }
  .page-header { flex-direction: column; align-items: flex-start; }
  .appointments-list { grid-template-columns: 1fr; }
}
</style>