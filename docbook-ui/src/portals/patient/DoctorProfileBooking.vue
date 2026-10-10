
<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { call } from "frappe-ui";
import { useRouter } from "vue-router";

const router = useRouter();

const doctors = ref([]);
const search = ref("");
const selectedDoctor = ref(null);
const selectedDate = ref("");
const selectedSlot = ref(null);
const slots = ref([]);

const loadingDoctors = ref(false);
const loadingSlots = ref(false);
const booking = ref(false);
const error = ref("");
const success = ref("");

const today = new Date();
today.setHours(0, 0, 0, 0);

const visibleMonth = ref(
  new Date(today.getFullYear(), today.getMonth(), 1)
);

const monthLabel = computed(() =>
  visibleMonth.value.toLocaleDateString("en-IN", {
    month: "long",
    year: "numeric",
  })
);

const filteredDoctors = computed(() => {
  const query = search.value.trim().toLowerCase();

  if (!query) return doctors.value;

  return doctors.value.filter((doctor) =>
    [
      doctor.full_name,
      doctor.name,
      doctor.specialty,
      doctor.qualification,
    ]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(query))
  );
});

const calendarDays = computed(() => {
  const year = visibleMonth.value.getFullYear();
  const month = visibleMonth.value.getMonth();

  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  // Leading empty cells keep the calendar aligned Sunday–Saturday.
  const cells = Array(firstDay).fill(null);

  for (let day = 1; day <= daysInMonth; day++) {
    const date = new Date(year, month, day);
    date.setHours(0, 0, 0, 0);

    cells.push({
      day,
      date: formatDate(date),
      disabled: date < today,
    });
  }

  while (cells.length % 7 !== 0) {
    cells.push(null);
  }

  return cells;
});

const consultationFee = computed(() => {
  if (!selectedDoctor.value) return null;

  return (
    selectedDoctor.value.consultation_fee ??
    selectedDoctor.value.fee ??
    null
  );
});

function formatDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

function isSameDate(dateString) {
  return selectedDate.value === dateString;
}

function previousMonth() {
  const current = visibleMonth.value;

  visibleMonth.value = new Date(
    current.getFullYear(),
    current.getMonth() - 1,
    1
  );
}

function nextMonth() {
  const current = visibleMonth.value;

  visibleMonth.value = new Date(
    current.getFullYear(),
    current.getMonth() + 1,
    1
  );
}

const isCurrentMonth = computed(() => {
  return (
    visibleMonth.value.getFullYear() === today.getFullYear() &&
    visibleMonth.value.getMonth() === today.getMonth()
  );
});

async function fetchDoctors() {
  loadingDoctors.value = true;
  error.value = "";

  try {
    const response = await call("docbook.api.doctor.list_doctors");

    const data = response?.message ?? response?.data ?? response;

    doctors.value = Array.isArray(data) ? data : [];
  } catch (err) {
    console.error("Failed to load doctors:", err);
    error.value = "Unable to load doctors. Please try again.";
  } finally {
    loadingDoctors.value = false;
  }
}

function chooseDoctor(doctor) {
  selectedDoctor.value = doctor;
  selectedDate.value = "";
  selectedSlot.value = null;
  slots.value = [];
  success.value = "";
  error.value = "";
}

async function chooseDate(date) {
  if (!selectedDoctor.value || !date) return;

  if (date < formatDate(today)) return;

  selectedDate.value = date;
  selectedSlot.value = null;
  slots.value = [];
  error.value = "";
  success.value = "";
  loadingSlots.value = true;

  try {
    /*
     * REQUIRED BACKEND METHOD:
     * docbook.api.appointment.get_available_slots
     *
     * Expected arguments:
     *   doctor: selectedDoctor.value.user || selectedDoctor.value.name
     *   date: selectedDate.value
     *
     * Expected response:
     *   [{ time: "09:00", label: "09:00 AM" }, ...]
     *
     * Implement this method in your Frappe app. It must calculate
     * the doctor's working hours and exclude already-booked slots.
     */
    const response = await call(
      "docbook.api.appointment.get_available_slots",
      {
        doctor:
          selectedDoctor.value.user || selectedDoctor.value.name,
        date: selectedDate.value,
      }
    );

    const data = response?.message ?? response?.data ?? response;

    slots.value = Array.isArray(data) ? data : [];
  } catch (err) {
    console.error("Failed to load available slots:", err);
    error.value =
      "Could not load availability. Make sure the backend availability API is implemented.";
  } finally {
    loadingSlots.value = false;
  }
}

function selectSlot(slot) {
  selectedSlot.value = slot;
  error.value = "";
  success.value = "";
}

async function bookAppointment() {
  if (!selectedDoctor.value || !selectedDate.value || !selectedSlot.value) {
    error.value = "Please select a doctor, date, and time slot.";
    return;
  }

  booking.value = true;
  error.value = "";
  success.value = "";

  try {
    /*
     * REQUIRED BACKEND METHOD:
     * docbook.api.appointment.book_appointment
     *
     * The backend must identify the patient from frappe.session.user.
     * It must verify the slot is still available and create the
     * appointment atomically to prevent double bookings.
     */
    const response = await call(
      "docbook.api.appointment.book_appointment",
      {
        doctor:
          selectedDoctor.value.user || selectedDoctor.value.name,
        date: selectedDate.value,
        time: selectedSlot.value.time,
      }
    );

    if (response?.message?.status === "error") {
      throw new Error(
        response.message.message || "Booking was not successful."
      );
    }

    success.value = "Appointment booked successfully!";

    // Refresh slots in case availability changed.
    await chooseDate(selectedDate.value);

    selectedSlot.value = null;

    // If desired, redirect to the appointments page after confirmation.
    // router.push("/my-appointments");
  } catch (err) {
    console.error("Booking failed:", err);
    error.value =
      err?.message || "Unable to book this appointment. Please try again.";
  } finally {
    booking.value = false;
  }
}

watch(visibleMonth, () => {
  if (
    selectedDate.value &&
    !selectedDate.value.startsWith(
      `${visibleMonth.value.getFullYear()}-${String(
        visibleMonth.value.getMonth() + 1
      ).padStart(2, "0")}`
    )
  ) {
    selectedDate.value = "";
    selectedSlot.value = null;
    slots.value = [];
  }
});

onMounted(fetchDoctors);
</script>

<template>
  <div class="min-h-screen bg-surface-secondary/40 px-4 py-6 sm:px-6 lg:px-8">
    <div class="mx-auto max-w-7xl space-y-7">

      <!-- Page heading -->
      <header class="space-y-2">
        <div
          class="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700"
        >
          <span class="size-2 rounded-full bg-blue-500"></span>
          DocBook Patient Portal
        </div>

        <h1 class="text-2xl font-bold tracking-tight text-ink-gray-9 sm:text-3xl">
          Book your appointment
        </h1>

        <p class="max-w-2xl text-sm leading-6 text-ink-gray-5 sm:text-base">
          Find the right doctor, select a convenient date, and reserve an
          available consultation slot.
        </p>
      </header>

      <!-- Alerts -->
      <div
        v-if="error"
        role="alert"
        class="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
      >
        {{ error }}
      </div>

      <div
        v-if="success"
        role="status"
        class="rounded-xl border border-green-200 bg-green-50 p-4 text-sm text-green-700"
      >
        {{ success }}
        <button
          type="button"
          class="ml-2 font-semibold underline"
          @click="router.push('/my-appointments')"
        >
          View appointments
        </button>
      </div>

      <!-- Search doctors -->
      <section class="space-y-4">
        <div class="flex items-center gap-3">
          <div class="flex size-10 items-center justify-center rounded-xl bg-blue-100 text-blue-700">
            <span class="iconify lucide-search size-5"></span>
          </div>
          <div>
            <h2 class="text-lg font-semibold text-ink-gray-9">
              1. Find your doctor
            </h2>
            <p class="text-sm text-ink-gray-5">
              Search by doctor name or specialty.
            </p>
          </div>
        </div>

        <div class="relative">
          <span
            class="iconify lucide-search absolute left-4 top-1/2 size-5 -translate-y-1/2 text-ink-gray-4"
          ></span>
          <input
            v-model="search"
            type="search"
            placeholder="Search cardiologist, dentist, doctor name..."
            class="w-full rounded-md border border-outline-gray-2 bg-surface-white py-4 pl-12 pr-4 text-sm outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
          />
        </div>

        <div v-if="loadingDoctors" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div
            v-for="n in 3"
            :key="n"
            class="h-36 animate-pulse rounded-2xl border border-outline-gray-1 bg-surface-white"
          ></div>
        </div>

        <div
          v-else-if="filteredDoctors.length"
          class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
        >
          <button
            v-for="doctor in filteredDoctors"
            :key="doctor.user || doctor.name"
            type="button"
            class="group rounded-2xl border bg-surface-white p-5 text-left transition hover:-translate-y-0.5 hover:border-blue-300 hover:shadow-md"
            :class="
              selectedDoctor?.name === doctor.name ||
              selectedDoctor?.user === doctor.user
                ? 'border-blue-500 ring-2 ring-blue-100'
                : 'border-outline-gray-1'
            "
            @click="chooseDoctor(doctor)"
          >
            <div class="flex items-start gap-3">
              <div
                class="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-100 to-teal-100 text-blue-700"
              >
                <span class="iconify lucide-stethoscope size-6"></span>
              </div>

              <div class="min-w-0 flex-1">
                <h3 class="truncate font-semibold text-ink-gray-9">
                  {{ doctor.full_name || doctor.name || "Doctor" }}
                </h3>
                <p class="mt-1 text-sm text-ink-gray-5">
                  {{ doctor.specialty || "General Practitioner" }}
                </p>
                <p class="mt-1 truncate text-xs text-ink-gray-4">
                  {{ doctor.qualification || "Qualified medical professional" }}
                </p>
              </div>

              <span
                v-if="
                  selectedDoctor?.name === doctor.name ||
                  selectedDoctor?.user === doctor.user
                "
                class="iconify lucide-check-circle-2 size-5 shrink-0 text-blue-600"
              ></span>
            </div>

            <div class="mt-5 flex items-center justify-between gap-2 border-t border-outline-gray-1 pt-4">
              <div>
                <p class="text-xs text-ink-gray-4">Consultation fee</p>
                <p class="mt-1 font-semibold text-ink-gray-9">
                  {{
                    doctor.consultation_fee != null
                      ? `₹${doctor.consultation_fee}`
                      : doctor.fee != null
                        ? `₹${doctor.fee}`
                        : "Contact clinic"
                  }}
                </p>
              </div>

              <span
                class="rounded-lg px-3 py-2 text-xs font-semibold transition"
                :class="
                  selectedDoctor?.name === doctor.name ||
                  selectedDoctor?.user === doctor.user
                    ? 'bg-blue-600 text-white'
                    : 'bg-blue-50 text-blue-700 group-hover:bg-blue-100'
                "
              >
                {{
                  selectedDoctor?.name === doctor.name ||
                  selectedDoctor?.user === doctor.user
                    ? "Selected"
                    : "Select doctor"
                }}
              </span>
            </div>
          </button>
        </div>

        <div
          v-else-if="!loadingDoctors"
          class="rounded-2xl border border-dashed border-outline-gray-2 bg-surface-white p-8 text-center"
        >
          <span class="iconify lucide-user-round-search mx-auto size-8 text-ink-gray-4"></span>
          <h3 class="mt-3 font-semibold text-ink-gray-9">No doctors found</h3>
          <p class="mt-1 text-sm text-ink-gray-5">
            Try searching with another name or specialty.
          </p>
        </div>
      </section>

      <!-- Calendar and slots -->
      <section
        class="grid items-start gap-6 lg:grid-cols-[1.15fr_0.85fr]"
      >
        <!-- Monthly calendar -->
        <div class="rounded-2xl border border-outline-gray-1 bg-surface-white p-4 shadow-sm sm:p-6">
          <div class="flex items-start gap-3">
            <div class="flex size-10 shrink-0 items-center justify-center rounded-xl bg-teal-50 text-teal-700">
              <span class="iconify lucide-calendar-days size-5"></span>
            </div>
            <div>
              <h2 class="font-semibold text-ink-gray-9">
                2. Choose a date
              </h2>
              <p class="mt-1 text-sm text-ink-gray-5">
                Select a date to check availability.
              </p>
            </div>
          </div>

          <div
            v-if="!selectedDoctor"
            class="mt-6 rounded-xl bg-surface-secondary p-5 text-center text-sm text-ink-gray-5"
          >
            Select a doctor above to start choosing a date.
          </div>

          <div v-else class="mt-6">
            <div class="mb-5 flex items-center justify-between gap-3">
              <button
                type="button"
                aria-label="Previous month"
                :disabled="isCurrentMonth"
                class="flex size-10 items-center justify-center rounded-xl border border-outline-gray-2 transition hover:bg-surface-secondary disabled:cursor-not-allowed disabled:opacity-30"
                @click="previousMonth"
              >
                <span class="iconify lucide-chevron-left size-5"></span>
              </button>

              <h3 class="text-base font-semibold text-ink-gray-9">
                {{ monthLabel }}
              </h3>

              <button
                type="button"
                aria-label="Next month"
                class="flex size-10 items-center justify-center rounded-xl border border-outline-gray-2 transition hover:bg-surface-secondary"
                @click="nextMonth"
              >
                <span class="iconify lucide-chevron-right size-5"></span>
              </button>
            </div>

            <div class="grid grid-cols-7 gap-y-2">
              <div
                v-for="day in ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']"
                :key="day"
                class="pb-3 text-center text-xs font-medium text-ink-gray-4"
              >
                {{ day }}
              </div>

              <div
                v-for="(cell, index) in calendarDays"
                :key="cell?.date || `empty-${index}`"
                class="flex items-center justify-center p-0.5 sm:p-1"
              >
                <button
                  v-if="cell"
                  type="button"
                  :disabled="cell.disabled"
                  :aria-pressed="isSameDate(cell.date)"
                  class="flex aspect-square w-full max-w-11 items-center justify-center rounded-xl text-sm transition"
                  :class="[
                    isSameDate(cell.date)
                      ? 'bg-blue-600 font-semibold text-white shadow-md shadow-blue-200'
                      : cell.disabled
                        ? 'cursor-not-allowed text-ink-gray-3'
                        : 'text-ink-gray-8 hover:bg-blue-50 hover:text-blue-700'
                  ]"
                  @click="chooseDate(cell.date)"
                >
                  {{ cell.day }}
                </button>
              </div>
            </div>

            <div class="mt-5 flex flex-wrap gap-x-4 gap-y-2 border-t border-outline-gray-1 pt-4 text-xs text-ink-gray-5">
              <div class="flex items-center gap-2">
                <span class="size-2.5 rounded-full bg-blue-600"></span>
                Selected date
              </div>
              <div class="flex items-center gap-2">
                <span class="size-2.5 rounded-full bg-outline-gray-2"></span>
                Past dates disabled
              </div>
            </div>

            <p class="mt-4 text-xs leading-5 text-ink-gray-4">
              Available dates and working days are confirmed by the booking
              system after you select a date.
            </p>
          </div>
        </div>

        <!-- Time slots -->
        <div class="rounded-2xl border border-outline-gray-1 bg-surface-white p-4 shadow-sm sm:p-6">
          <div class="flex items-start gap-3">
            <div class="flex size-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-700">
              <span class="iconify lucide-clock-3 size-5"></span>
            </div>
            <div>
              <h2 class="font-semibold text-ink-gray-9">
                3. Available time slots
              </h2>
              <p class="mt-1 text-sm text-ink-gray-5">
                Choose your preferred consultation time.
              </p>
            </div>
          </div>

          <div
            v-if="!selectedDoctor"
            class="mt-6 rounded-xl bg-surface-secondary p-5 text-center text-sm text-ink-gray-5"
          >
            Choose a doctor first.
          </div>

          <div
            v-else-if="!selectedDate"
            class="mt-6 rounded-xl bg-surface-secondary p-5 text-center"
          >
            <span class="iconify lucide-calendar-clock mx-auto size-8 text-ink-gray-4"></span>
            <p class="mt-3 text-sm font-medium text-ink-gray-7">
              Select a date on the calendar
            </p>
            <p class="mt-1 text-xs text-ink-gray-5">
              Available time slots will appear here.
            </p>
          </div>

          <div v-else class="mt-6">
            <div class="mb-4 rounded-xl bg-blue-50 p-3">
              <p class="text-xs text-blue-700">Selected date</p>
              <p class="mt-1 font-semibold text-blue-950">
                {{
                  new Date(`${selectedDate}T12:00:00`).toLocaleDateString(
                    "en-IN",
                    {
                      weekday: "long",
                      day: "numeric",
                      month: "long",
                      year: "numeric",
                    }
                  )
                }}
              </p>
            </div>

            <div v-if="loadingSlots" class="space-y-3">
              <div
                v-for="n in 4"
                :key="n"
                class="h-11 animate-pulse rounded-xl bg-surface-secondary"
              ></div>
            </div>

            <div
              v-else-if="slots.length"
              class="grid grid-cols-2 gap-3"
            >
              <button
                v-for="slot in slots"
                :key="slot.time"
                type="button"
                :disabled="slot.available === false || slot.booked === true"
                class="rounded-xl border px-3 py-3 text-sm font-medium transition"
                :class="
                  selectedSlot?.time === slot.time
                    ? 'border-blue-600 bg-blue-600 text-white shadow-md shadow-blue-100'
                    : slot.available === false || slot.booked === true
                      ? 'cursor-not-allowed border-outline-gray-1 bg-surface-secondary text-ink-gray-3 line-through'
                      : 'border-outline-gray-2 text-ink-gray-8 hover:border-blue-400 hover:bg-blue-50'
                "
                @click="selectSlot(slot)"
              >
                {{ slot.label || slot.time }}
              </button>
            </div>

            <div
              v-else
              class="rounded-xl border border-dashed border-outline-gray-2 p-6 text-center"
            >
              <span class="iconify lucide-calendar-x mx-auto size-8 text-ink-gray-4"></span>
              <p class="mt-3 text-sm font-medium text-ink-gray-8">
                No available slots
              </p>
              <p class="mt-1 text-xs text-ink-gray-5">
                Select another date to check availability.
              </p>
            </div>

            <p v-if="slots.length" class="mt-4 text-xs text-ink-gray-5">
              Select an available time to continue.
            </p>
          </div>
        </div>
      </section>

      <!-- Booking summary -->
      <section
        v-if="selectedDoctor && selectedDate && selectedSlot"
        class="overflow-hidden rounded-2xl border border-blue-100 bg-surface-white shadow-sm"
      >
        <div class="bg-gradient-to-r from-blue-600 to-teal-600 px-5 py-4 text-white sm:px-6">
          <div class="flex items-center gap-2">
            <span class="iconify lucide-clipboard-check size-5"></span>
            <h2 class="font-semibold">4. Confirm your appointment</h2>
          </div>
          <p class="mt-1 text-sm text-blue-50">
            Review the details before booking.
          </p>
        </div>

        <div class="grid gap-5 p-5 sm:grid-cols-2 sm:p-6 lg:grid-cols-4">
          <div>
            <p class="text-xs text-ink-gray-4">Doctor</p>
            <p class="mt-1 font-semibold text-ink-gray-9">
              {{ selectedDoctor.full_name || selectedDoctor.name }}
            </p>
            <p class="mt-1 text-xs text-ink-gray-5">
              {{ selectedDoctor.specialty || "Doctor" }}
            </p>
          </div>

          <div>
            <p class="text-xs text-ink-gray-4">Date</p>
            <p class="mt-1 font-semibold text-ink-gray-9">
              {{
                new Date(`${selectedDate}T12:00:00`).toLocaleDateString(
                  "en-IN",
                  { day: "numeric", month: "short", year: "numeric" }
                )
              }}
            </p>
          </div>

          <div>
            <p class="text-xs text-ink-gray-4">Time</p>
            <p class="mt-1 font-semibold text-ink-gray-9">
              {{ selectedSlot.label || selectedSlot.time }}
            </p>
          </div>

          <div>
            <p class="text-xs text-ink-gray-4">Consultation fee</p>
            <p class="mt-1 font-semibold text-ink-gray-9">
              {{
                consultationFee != null
                  ? `₹${consultationFee}`
                  : "Confirm with clinic"
              }}
            </p>
          </div>
        </div>

        <div class="flex flex-col gap-3 border-t border-outline-gray-1 p-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <p class="text-xs leading-5 text-ink-gray-5">
            Your booking is confirmed only after the server accepts it.
          </p>

          <button
            type="button"
            :disabled="booking"
            class="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-blue-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            @click="bookAppointment"
          >
            <span
              v-if="booking"
              class="iconify lucide-loader-circle size-4 animate-spin"
            ></span>
            <span v-else class="iconify lucide-calendar-check size-4"></span>
            {{ booking ? "Booking..." : "Book appointment" }}
          </button>
        </div>
      </section>

    </div>
  </div>
</template>