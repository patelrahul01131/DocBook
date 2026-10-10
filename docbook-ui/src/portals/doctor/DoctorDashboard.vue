<script setup>
import { computed, onMounted, ref } from 'vue'
import { Badge, Button } from 'frappe-ui'
import { useRouter } from 'vue-router'
import { call } from '../../api'

const router = useRouter()

const doctors = ref([])
const searchQuery = ref('')
const loading = ref(false)
const refreshing = ref(false)
const error = ref('')

const fetchDoctors = async (isRefresh = false) => {
  if (isRefresh) {
    refreshing.value = true
  } else {
    loading.value = true
  }

  error.value = ''

  try {
    const result = await call('docbook.api.doctor.list_doctors')
    doctors.value = Array.isArray(result) ? result : []
  } catch (err) {
    console.error('Failed to load doctors:', err)
    error.value = 'Unable to load doctors. Please try again.'
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

const filteredDoctors = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()

  if (!query) return doctors.value

  return doctors.value.filter((doctor) => {
    const searchable = [
      doctor.full_name,
      doctor.doctor_name,
      doctor.name,
      doctor.specialty,
      doctor.qualification,
    ]

    return searchable.some((value) =>
      String(value || '').toLowerCase().includes(query)
    )
  })
})

const specialtyCount = computed(() => {
  return new Set(
    doctors.value
      .map((doctor) => doctor.specialty?.trim())
      .filter(Boolean)
      .map((specialty) => specialty.toLowerCase())
  ).size
})

const averageRating = computed(() => {
  const ratings = doctors.value
    .map((doctor) => Number(doctor.rating))
    .filter((rating) => Number.isFinite(rating) && rating > 0)

  if (!ratings.length) return null

  return (
    ratings.reduce((total, rating) => total + rating, 0) /
    ratings.length
  ).toFixed(1)
})

const doctorName = (doctor) =>
  doctor.full_name || doctor.doctor_name || doctor.name || 'Doctor'

const formatFee = (fee) => {
  const amount = Number(fee)

  if (fee == null || fee === '' || !Number.isFinite(amount)) {
    return 'Not specified'
  }

  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(amount)
}

const viewDoctor = (doctor) => {
  const identifier = doctor.user || doctor.name

  if (!identifier) return

  router.push({
    path: '/doctor_profile',
    query: { doctor: identifier },
  })
}

const findDoctors = () => {
  router.push('/find-doctors')
}

onMounted(() => {
  fetchDoctors()
})
</script>

<template>
  <main class="dashboard-page">
    <div class="dashboard-shell">

      <!-- Header -->
      <header class="dashboard-header">
        <div class="heading-copy">
          <div class="eyebrow">
            <span class="lucide-layout-dashboard"></span>
            DOCBOOK / OVERVIEW
          </div>

          <h1>Doctor Dashboard<span>.</span></h1>

          <p>
            Manage your doctor directory and explore healthcare
            professionals in one place.
          </p>
        </div>

        <div class="header-actions">
          <Button
            label="Refresh"
            icon-left="lucide-refresh-cw"
            :loading="refreshing"
            :disabled="loading || refreshing"
            @click="fetchDoctors(true)"
          />

          <Button
            label="Find doctors"
            icon-left="lucide-arrow-up-right"
            @click="findDoctors"
          />
        </div>
      </header>

      <!-- Summary cards -->
      <section class="stats-grid" aria-label="Dashboard statistics">

        <article class="stat-card">
          <div class="stat-top">
            <span class="stat-icon blue">
              <span class="lucide-users"></span>
            </span>
            <Badge theme="blue">Directory</Badge>
          </div>

          <p class="stat-label">Total doctors</p>

          <h2>
            {{ loading ? '—' : doctors.length }}
          </h2>

          <p class="stat-caption">Doctors returned by the directory API</p>
        </article>

        <article class="stat-card">
          <div class="stat-top">
            <span class="stat-icon teal">
              <span class="lucide-stethoscope"></span>
            </span>
            <Badge theme="green">Specialties</Badge>
          </div>

          <p class="stat-label">Specialties covered</p>

          <h2>{{ loading ? '—' : specialtyCount }}</h2>

          <p class="stat-caption">Distinct specialties in the directory</p>
        </article>

        <article class="stat-card">
          <div class="stat-top">
            <span class="stat-icon amber">
              <span class="lucide-star"></span>
            </span>
            <Badge>Patient ratings</Badge>
          </div>

          <h2 class="rating-number">
            {{ loading ? '—' : averageRating ?? '—' }}
            <span v-if="averageRating" class="rating-star">★</span>
          </h2>

          <p class="stat-caption">
            Average of available doctor ratings
          </p>
        </article>
      </section>

      <!-- Directory -->
      <section class="directory-section">
        <div class="section-heading">
          <div>
            <div class="eyebrow">YOUR DIRECTORY</div>
            <h2>Explore doctors</h2>
            <p>Find the right professional for your healthcare needs.</p>
          </div>

          <Badge>{{ filteredDoctors.length }} results</Badge>
        </div>

        <div class="toolbar">
          <div class="search-box">
            <span class="lucide-search search-icon"></span>
            <Input
              v-model="searchQuery"
              placeholder="Search name, specialty or qualification..."
              class="doctor-search border-none outline-none"
            />
            <button
              v-if="searchQuery"
              class="clear-search"
              type="button"
              aria-label="Clear search"
              @click="searchQuery = ''"
            >
              <span class="lucide-x"></span>
            </button>
          </div>
        </div>

        <!-- Error -->
        <div v-if="error" class="feedback-card error-card">
          <span class="lucide-circle-alert feedback-icon"></span>
          <div>
            <h3>Something went wrong</h3>
            <p>{{ error }}</p>
          </div>
          <Button
            label="Try again"
            icon-left="lucide-refresh-cw"
            @click="fetchDoctors()"
          />
        </div>

        <!-- Loading skeletons -->
        <div v-else-if="loading" class="doctor-grid">
          <div
            v-for="item in 6"
            :key="item"
            class="doctor-card skeleton-card"
          >
            <div class="skeleton skeleton-avatar"></div>
            <div class="skeleton skeleton-line wide"></div>
            <div class="skeleton skeleton-line"></div>
            <div class="skeleton skeleton-block"></div>
          </div>
        </div>

        <!-- Empty directory -->
        <div
          v-else-if="!doctors.length"
          class="feedback-card empty-card"
        >
          <span class="lucide-stethoscope feedback-icon"></span>
          <h3>No doctors available yet</h3>
          <p>
            Doctor profiles will appear here when they are returned by
            your API.
          </p>
          <Button
            label="Refresh directory"
            icon-left="lucide-refresh-cw"
            @click="fetchDoctors()"
          />
        </div>

        <!-- No search results -->
        <div
          v-else-if="!filteredDoctors.length"
          class="feedback-card empty-card"
        >
          <span class="lucide-search feedback-icon"></span>
          <h3>No matching doctors</h3>
          <p>Try another name, specialty or qualification.</p>
          <Button
            label="Clear search"
            @click="searchQuery = ''"
          />
        </div>

        <!-- Doctor cards -->
        <div v-else class="doctor-grid">
          <article
            v-for="(doctor, index) in filteredDoctors"
            :key="doctor.name || doctor.user || index"
            class="doctor-card"
          >
            <div class="doctor-card-top">
              <div class="doctor-avatar">
                <span class="lucide-user-round"></span>
              </div>

              <Badge theme="blue">
                {{ doctor.specialty || 'General practice' }}
              </Badge>
            </div>

            <h3 class="doctor-name">{{ doctorName(doctor) }}</h3>

            <p class="doctor-qualification">
              {{ doctor.qualification || 'Qualification not specified' }}
            </p>

            <div class="doctor-details">
              <div class="detail-row">
                <span class="lucide-briefcase-medical"></span>
                <span>Experience</span>
                <strong>
                  {{
                    doctor.experience_years != null
                      ? `${doctor.experience_years} years`
                      : 'Not specified'
                  }}
                </strong>
              </div>

              <div class="detail-row">
                <span class="lucide-star"></span>
                <span>Rating</span>
                <strong>
                  {{
                    doctor.rating != null && doctor.rating !== ''
                      ? `★ ${doctor.rating}`
                      : 'Not rated'
                  }}
                </strong>
              </div>
            </div>

            <div class="doctor-card-footer">
              <div class="fee-block">
                <span>Consultation fee</span>
                <strong>{{ formatFee(doctor.consultation_fee) }}</strong>
              </div>

              <Button
                label="View profile"
                icon-right="lucide-arrow-up-right"
                @click="viewDoctor(doctor)"
              />
            </div>
          </article>
        </div>
      </section>

      <!-- Bottom banner -->
      <section class="dashboard-banner">
        <div class="banner-icon">
          <span class="lucide-heart-pulse"></span>
        </div>

        <div class="banner-copy">
          <h2>Healthcare made simpler.</h2>
          <p>
            Keep your doctor directory accessible and your patient
            experience seamless with DocBook.
          </p>
        </div>

        <Button
          label="Open appointments"
          icon-right="lucide-arrow-up-right"
          @click="router.push('/my-appointments')"
        />
      </section>

      <footer class="dashboard-footer">
        <span>DocBook · Healthcare made simple</span>
        <span>Doctor directory dashboard</span>
      </footer>

    </div>
  </main>
</template>

<style scoped>
.dashboard-page {
  --db-blue: #2563eb;
  --db-teal: #0d9488;
  --db-ink: #0f172a;
  --db-muted: #64748b;
  --db-border: rgba(226, 232, 240, 0.9);

  min-height: 100%;
  padding: 36px 24px 28px;
  color: var(--db-ink);
  background:
    radial-gradient(ellipse at 0% 0%, rgba(37, 99, 235, .08), transparent 34%),
    radial-gradient(ellipse at 100% 40%, rgba(20, 184, 166, .07), transparent 30%),
    #f4f7fb;
}

.dashboard-shell {
  width: 100%;
  max-width: 1320px;
  margin: 0 auto;
}

.dashboard-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 30px;
}

.heading-copy {
  min-width: 0;
}

.eyebrow {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--db-blue);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 1.5px;
}

.heading-copy h1 {
  margin: 12px 0 8px;
  font-size: clamp(30px, 3.3vw, 43px);
  font-weight: 780;
  letter-spacing: -1.8px;
  line-height: 1.12;
}

.heading-copy h1 span {
  color: var(--db-teal);
}

.heading-copy > p,
.section-heading p {
  margin: 0;
  color: var(--db-muted);
  font-size: 14px;
  line-height: 1.7;
}

.header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  flex-shrink: 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
  margin-bottom: 38px;
}

.stat-card {
  min-width: 0;
  padding: 22px;
  border: 1px solid rgba(255, 255, 255, .9);
  border-radius: 22px;
  background: rgba(255, 255, 255, .8);
  box-shadow: 0 12px 32px rgba(15, 23, 42, .045);
  backdrop-filter: blur(18px);
}

.stat-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 22px;
}

.stat-icon {
  display: grid;
  width: 44px;
  height: 44px;
  place-items: center;
  border-radius: 14px;
  font-size: 19px;
}

.stat-icon.blue {
  color: #2563eb;
  background: #eff6ff;
}

.stat-icon.teal {
  color: #0f766e;
  background: #ccfbf1;
}

.stat-icon.amber {
  color: #b45309;
  background: #fef3c7;
}

.stat-label {
  margin: 0 0 5px;
  color: var(--db-muted);
  font-size: 12px;
  font-weight: 600;
}

.stat-card h2 {
  margin: 0;
  font-size: 32px;
  font-weight: 780;
  letter-spacing: -1px;
}

.stat-caption {
  margin: 8px 0 0;
  color: #94a3b8;
  font-size: 11px;
  line-height: 1.5;
}

.rating-number {
  display: flex;
  align-items: center;
  gap: 7px;
}

.rating-star {
  color: #f59e0b;
  font-size: 20px;
}

.directory-section {
  min-width: 0;
}

.section-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 22px;
}

.section-heading h2 {
  margin: 7px 0 5px;
  font-size: 25px;
  font-weight: 750;
  letter-spacing: -.8px;
}

.toolbar {
  margin-bottom: 20px;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 10px;
  max-width: 540px;
  min-height: 48px;
  padding: 0 14px;
  border: none;
  outline: none;
  border-radius: 15px;
  background: rgba(255, 255, 255, .88);
  box-shadow: 0 4px 16px rgba(15, 23, 42, .025);
}

.search-icon {
  flex-shrink: 0;
  color: #94a3b8;
}

.doctor-search {
  min-width: 0;
  flex: 1;
}

.clear-search {
  display: grid;
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  place-items: center;
  border: 0;
  border-radius: 8px;
  background: #f1f5f9;
  color: #64748b;
  cursor: pointer;
}

.doctor-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.doctor-card {
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: 21px;
  border: 1px solid rgba(255, 255, 255, .95);
  border-radius: 23px;
  background: rgba(255, 255, 255, .86);
  box-shadow: 0 10px 28px rgba(15, 23, 42, .045);
  transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease;
}

.doctor-card:hover {
  transform: translateY(-4px);
  border-color: #bfdbfe;
  box-shadow: 0 20px 38px rgba(15, 23, 42, .08);
}

.doctor-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 19px;
}

.doctor-avatar {
  display: grid;
  width: 54px;
  height: 54px;
  flex-shrink: 0;
  place-items: center;
  border: 1px solid #dbeafe;
  border-radius: 17px;
  background: linear-gradient(135deg, #eff6ff, #ccfbf1);
  color: var(--db-blue);
  font-size: 23px;
}

.doctor-name {
  overflow-wrap: anywhere;
  margin: 0;
  font-size: 17px;
  font-weight: 750;
  letter-spacing: -.35px;
}

.doctor-qualification {
  min-height: 36px;
  margin: 6px 0 18px;
  color: var(--db-muted);
  font-size: 12px;
  line-height: 1.6;
}

.doctor-details {
  display: grid;
  gap: 12px;
  padding: 16px 0;
  border-top: 1px solid #f1f5f9;
  border-bottom: 1px solid #f1f5f9;
}

.detail-row {
  display: grid;
  grid-template-columns: 16px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  color: var(--db-muted);
  font-size: 11px;
}

.detail-row > span:first-child {
  color: var(--db-teal);
}

.detail-row strong {
  max-width: 130px;
  overflow-wrap: anywhere;
  color: #334155;
  font-size: 11px;
  font-weight: 700;
  text-align: right;
}

.doctor-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: auto;
  padding-top: 17px;
}

.fee-block {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}

.fee-block > span {
  color: #94a3b8;
  font-size: 10px;
}

.fee-block strong {
  overflow-wrap: anywhere;
  font-size: 14px;
  font-weight: 800;
}

.feedback-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 25px;
  border: 1px solid var(--db-border);
  border-radius: 22px;
  background: rgba(255, 255, 255, .88);
}

.feedback-card h3 {
  margin: 0 0 5px;
  font-size: 15px;
}

.feedback-card p {
  margin: 0;
  color: var(--db-muted);
  font-size: 12px;
  line-height: 1.6;
}

.feedback-icon {
  flex-shrink: 0;
  color: var(--db-blue);
  font-size: 24px;
}

.empty-card {
  flex-direction: column;
  align-items: center;
  padding: 48px 20px;
  text-align: center;
}

.error-card {
  border-color: #fecaca;
  background: #fffafa;
}

.error-card .feedback-icon {
  color: #dc2626;
}

.skeleton-card {
  gap: 14px;
}

.skeleton {
  border-radius: 9px;
  background: linear-gradient(90deg, #f1f5f9, #e2e8f0, #f1f5f9);
  background-size: 200% 100%;
  animation: shimmer 1.5s linear infinite;
}

.skeleton-avatar {
  width: 54px;
  height: 54px;
  border-radius: 17px;
}

.skeleton-line {
  width: 60%;
  height: 12px;
}

.skeleton-line.wide {
  width: 85%;
  height: 17px;
}

.skeleton-block {
  width: 100%;
  height: 70px;
  margin-top: 8px;
}

@keyframes shimmer {
  to { background-position: -200% 0; }
}

.dashboard-banner {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-top: 42px;
  padding: 26px;
  border: 1px solid rgba(255, 255, 255, .15);
  border-radius: 24px;
  background: linear-gradient(125deg, #0f172a, #172554 68%, #134e4a);
  color: white;
  box-shadow: 0 18px 40px rgba(15, 23, 42, .12);
}

.banner-icon {
  display: grid;
  width: 52px;
  height: 52px;
  flex-shrink: 0;
  place-items: center;
  border-radius: 16px;
  background: rgba(255, 255, 255, .1);
  color: #5eead4;
  font-size: 23px;
}

.banner-copy {
  flex: 1;
  min-width: 0;
}

.banner-copy h2 {
  margin: 0 0 6px;
  font-size: 18px;
  font-weight: 750;
}

.banner-copy p {
  max-width: 580px;
  margin: 0;
  color: #cbd5e1;
  font-size: 12px;
  line-height: 1.7;
}

.dashboard-footer {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-top: 24px;
  padding: 18px 2px 0;
  border-top: 1px solid var(--db-border);
  color: #94a3b8;
  font-size: 11px;
}

@media (max-width: 1100px) {
  .doctor-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .dashboard-header {
    align-items: flex-start;
    flex-direction: column;
  }
}

@media (max-width: 760px) {
  .dashboard-page {
    padding: 25px 18px;
  }

  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .stat-card {
    padding: 17px;
  }

  .stat-card:last-child {
    grid-column: 1 / -1;
  }

  .doctor-grid {
    gap: 13px;
  }

  .dashboard-banner {
    align-items: flex-start;
    flex-wrap: wrap;
    padding: 22px;
  }

  .banner-copy {
    flex-basis: calc(100% - 75px);
  }

  .dashboard-banner > :last-child {
    width: 100%;
  }
}

@media (max-width: 520px) {
  .dashboard-page {
    padding: 20px 13px;
  }

  .heading-copy h1 {
    font-size: 32px;
    letter-spacing: -1.2px;
  }

  .heading-copy > p {
    font-size: 12px;
  }

  .header-actions {
    width: 100%;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .stat-card:last-child {
    grid-column: auto;
  }

  .stat-top {
    margin-bottom: 14px;
  }

  .section-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .doctor-grid {
    grid-template-columns: 1fr;
  }

  .doctor-card {
    padding: 19px;
  }

  .doctor-qualification {
    min-height: 0;
  }

  .search-box {
    gap: 7px;
    padding: 0 10px;
  }

  .feedback-card:not(.empty-card) {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .dashboard-footer {
    flex-direction: column;
    gap: 7px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .doctor-card,
  .skeleton {
    animation: none;
    transition: none;
  }
}
</style>
