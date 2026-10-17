<script setup>
import { Button } from 'frappe-ui'
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { call } from '../../api'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const symptoms = ref('')
const aiLoading = ref(false)
const aiError = ref(null)
const aiReasoning = ref('')
const detectedSpecialty = ref(null)
const aiUrgency = ref('')

const doctors = ref([])
const doctorsLoading = ref(false)
const doctorsError = ref(null)
const showNoDoctor = ref(false)

const quickSymptoms = [
  'Chest pain and shortness of breath',
  'Skin rash and itching',
  'Severe headache and dizziness',
  'Knee injury and swelling',
  'Fever and sore throat',
  'Back pain and numbness',
  'Stomach pain and nausea',
  'Eye redness and irritation',
]

function isValidSymptomInput(text) {
  const t = text.trim()
  if (t.length < 3) return false
  // Must contain at least one alphabetic character
  if (!/[a-zA-Z]/.test(t)) return false
  // Reject all-same-character repeats (e.g. "aaaa", "!!!!")
  if (/^(.)\1+$/.test(t)) return false
  return true
}

async function analyzeSymptoms() {
  const raw = symptoms.value.trim()
  if (!raw) {
    aiError.value = 'Please describe your problem or symptoms.'
    return
  }
  if (!isValidSymptomInput(raw)) {
    aiError.value = 'Please enter a valid symptom or health problem (e.g. "chest pain", "skin rash").'
    return
  }
  aiLoading.value = true
  aiError.value = null
  detectedSpecialty.value = null
  doctors.value = []
  showNoDoctor.value = false
  try {
    const res = await call('docbook.api.appointment.ai_assign_doctor', {
      symptoms: symptoms.value,
      preferred_date: null,
      preferred_time: null,
    })
    aiReasoning.value = res.ai_reasoning || ''
    aiUrgency.value = res.ai_urgency || 'medium'
    const specialties = res.matched_specialties || []
    if (specialties.length) {
      detectedSpecialty.value = specialties[0]
    }
    if (res.doctors_available === false) {
      showNoDoctor.value = true
    } else {
      await fetchDoctorsBySpecialty(detectedSpecialty.value)
    }
  } catch (e) {
    aiError.value = e.message || 'AI analysis failed. Please try again.'
  } finally {
    aiLoading.value = false
  }
}

async function fetchDoctorsBySpecialty(specialty) {
  if (!specialty) {
    showNoDoctor.value = true
    return
  }
  doctorsLoading.value = true
  doctorsError.value = null
  try {
    const res = await call('docbook.api.doctor.get_doctors_by_specialty', {
      specialty: specialty,
    })
    const list = Array.isArray(res) ? res : []
    doctors.value = list.map(d => ({
      user: d.user,
      full_name: d.full_name,
      specialty: d.specialty,
      qualification: d.qualification,
      experience_years: d.experience_years,
      consultation_fee: d.consultation_fee,
      rating: d.rating,
      phone: d.phone,
      bio: d.bio,
      profile_image: d.profile_image,
    }))
    if (doctors.value.length === 0) {
      showNoDoctor.value = true
    }
  } catch (e) {
    doctorsError.value = e.message || 'Failed to load doctors.'
    showNoDoctor.value = true
  } finally {
    doctorsLoading.value = false
  }
}

function viewDoctor(doctor) {
  router.push({ path: '/doctor_profile', query: { doctor: doctor.user } })
}

function urgencyLabel(u) {
  const map = { low: 'Low', medium: 'Medium', high: 'High', critical: 'Critical' }
  return map[u] || 'Medium'
}
function urgencyClass(u) {
  const map = {
    low: 'ai-urgency--low',
    medium: 'ai-urgency--medium',
    high: 'ai-urgency--high',
    critical: 'ai-urgency--critical',
  }
  return map[u] || 'ai-urgency--medium'
}
function resetFlow() {
  symptoms.value = ''
  aiError.value = null
  detectedSpecialty.value = null
  doctors.value = []
  showNoDoctor.value = false
  doctorsError.value = null
}
</script>

<template>
  <div class="home-page">
    <section class="hero-section">
      <div class="hero-container">
        <div class="hero-content">
          <div class="hero-badge">AI-Powered Doctor Matching</div>
          <h1>Find the right<br /><span class="text-gradient">doctor for you</span></h1>
          <p class="hero-description">Describe your symptoms and our AI triage matches you with the right specialist, then book instantly.</p>

          <div class="search-card">
            <div class="search-header">
              <div class="search-icon">🔍</div>
              <div>
                <h3>What's bothering you?</h3>
                <p>Describe your symptoms in your own words.</p>
              </div>
            </div>
            <textarea v-model="symptoms" rows="4" placeholder="e.g. chest pain, skin rash, headache, knee injury, fever..." class="ai-textarea"></textarea>

            <div class="ai-input-actions">
              <button class="ai-analyze-btn" :disabled="aiLoading || !symptoms.trim()" @click="analyzeSymptoms">
                <span v-if="aiLoading" class="ai-btn-loading">
                  <span class="ai-spinner"></span>
                  <span>Analyzing symptoms…</span>
                </span>
                <span v-else>Find Doctor with AI</span>
              </button>
            </div>

            <div v-if="aiError" class="ai-error">{{ aiError }}</div>

            <div v-if="detectedSpecialty" class="ai-result-card">
              <div class="ai-result-header">
                <span class="ai-badge ai-urgency-badge" :class="urgencyClass(aiUrgency)">
                  {{ urgencyLabel(aiUrgency) }} Urgency
                </span>
                <span class="ai-specialty-chip">🎯 {{ detectedSpecialty }}</span>
              </div>
              <div v-if="aiReasoning" class="ai-reasoning-box">
                <span class="ai-reasoning-label">AI Reasoning:</span>
                <p class="ai-reasoning-text">{{ aiReasoning }}</p>
              </div>
            </div>

            <div v-if="showNoDoctor && detectedSpecialty" class="empty-state">
              <div class="empty-icon">😔</div>
              <h3>No doctors available</h3>
              <p>We couldn't find any approved {{ detectedSpecialty }} specialist for "{{ symptoms }}".</p>
              <Button label="Try another problem" variant="outline" @click="resetFlow" />
            </div>

            <div v-if="doctorsLoading" class="ai-loading">
              <span class="loading-dots">Finding doctors<span class="dots">...</span></span>
            </div>

            <div v-if="doctorsError" class="ai-error">{{ doctorsError }}</div>

            <div v-if="doctors.length > 0" class="doctors-section">
              <div class="doctors-header">
                <h3>Available {{ detectedSpecialty }} Doctors</h3>
                <p>{{ doctors.length }} doctor{{ doctors.length !== 1 ? 's' : '' }} found</p>
              </div>
              <div class="doctors-grid">
                <div v-for="doc in doctors" :key="doc.user" class="doctor-card" @click="viewDoctor(doc)">
                  <div class="doctor-avatar">
                    <span class="avatar-letter">{{ doc.full_name.charAt(0) }}</span>
                  </div>
                  <div class="doctor-info">
                    <div class="doctor-name">{{ doc.full_name }}</div>
                    <div class="doctor-specialty">{{ doc.specialty }}</div>
                    <div class="doctor-meta">
                      <span class="doctor-qual">{{ doc.qualification }}</span>
                      <span class="doctor-divider">·</span>
                      <span class="doctor-exp">{{ doc.experience_years }} years exp.</span>
                    </div>
                    <div class="doctor-rating-row">
                      <div class="doctor-rating">
                        <span class="star">★</span>
                        <span class="rating-val">{{ doc.rating || 'N/A' }}</span>
                      </div>
                      <div class="doctor-fee">₹{{ doc.consultation_fee }}</div>
                    </div>
                  </div>
                  <button class="book-btn w-full" @click.stop="viewDoctor(doc)">Book Appointment</button>
                </div>
              </div>
            </div>
          </div>

          <div class="quick-symptoms">
            <p class="quick-label">Or try a common symptom:</p>
            <div class="quick-chips">
              <button v-for="s in quickSymptoms" :key="s" class="quick-chip" @click="symptoms = s">{{ s }}</button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="features-section">
      <div class="features-container">
        <div class="feature-card">
          <div class="feature-icon">🤖</div>
          <h3>AI-Powered Triage</h3>
          <p>Smart symptom analysis matches you with the right specialist instantly.</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">⚡</div>
          <h3>Instant Booking</h3>
          <p>Book appointments with verified doctors in a few taps — no waiting.</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">📄</div>
          <h3>Medical Reports</h3>
          <p>Upload and preview lab results, imaging, and prescriptions securely.</p>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.home-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
  color: #0f172a;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  line-height: 1.5;
}
.background-orb {
  position: fixed;
  border-radius: 50%;
  filter: blur(80px);
  z-index: -1;
  opacity: 0.4;
}
.orb-blue {
  top: -10%;
  left: -10%;
  width: 500px;
  height: 500px;
  background: #0e7490;
}
.orb-teal {
  bottom: -10%;
  right: -10%;
  width: 600px;
  height: 600px;
  background: #0d9488;
}
.top-nav {
  position: sticky;
  top: 0;
  z-index: 50;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid #e2e8f0;
}
.nav-container {
  max-width: 1100px;
  margin: 0 auto;
  padding: 14px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}
.nav-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 800;
  letter-spacing: -0.5px;
}
.nav-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.hero-section {
  padding: 20px 24px 60px;
  position: relative;
}
.hero-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 0 24px;
}
.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  background: #f0fdfa;
  color: #0d9488;
  border: 1px solid #99f6e4;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  margin-bottom: 16px;
}
.hero-content h1 {
  font-size: clamp(40px, 7vw, 64px);
  font-weight: 900;
  line-height: 1.1;
  letter-spacing: -1px;
  margin: 0 0 18px;
}
.hero-content h1 .text-gradient {
  background: linear-gradient(135deg, #0d9488, #0e7490);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.hero-description {
  font-size: 18px;
  color: #475569;
  margin: 0 0 28px;
  line-height: 1.7;
  max-width: 520px;
}
.search-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 24px;
  padding: 32px;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.08);
}
.search-header {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  margin-bottom: 24px;
}
.search-icon {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0fdfa;
  color: #0d9488;
  font-size: 20px;
  flex-shrink: 0;
}
.search-header h3 {
  margin: 0 0 4px;
  font-size: 17px;
  font-weight: 800;
}
.search-header p {
  margin: 0;
  font-size: 13px;
  color: #64748b;
}
.ai-textarea {
  width: 100%;
  padding: 16px 18px;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  font-family: inherit;
  font-size: 15px;
  resize: vertical;
  min-height: 110px;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.ai-textarea:focus {
  outline: none;
  border-color: #0d9488;
  box-shadow: 0 0 0 4px rgba(13, 148, 136, 0.1);
}
.ai-input-actions {
  display: flex;
  gap: 10px;
}
.ai-analyze-btn {
  flex: 1;
  padding: 16px 24px;
  border: none;
  border-radius: 14px;
  background: #0d9488;
  color: #fff;
  font-weight: 800;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.2s;
}
.ai-analyze-btn:hover:not(:disabled) {
  background: #0b7976;
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(13, 148, 136, 0.25);
}
.ai-analyze-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.ai-btn-loading {
  display: flex;
  align-items: center;
  gap: 8px;
}
.ai-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.35);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.ai-error {
  background: #fef2f2;
  color: #b91c1c;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 13px;
  margin-top: 12px;
  border: 1px solid #fecaca;
}
.ai-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #0d9488;
  font-weight: 600;
  font-size: 14px;
  margin-top: 12px;
}
.dots {
  animation: pulse 1.5s infinite;
}
@keyframes pulse {
  0%,
  100% {
    opacity: 0.4;
  }
  50% {
    opacity: 1;
  }
}
.ai-result-card {
  margin-top: 18px;
  padding: 20px;
  background: linear-gradient(135deg, #f0fdfa, #ecfdf5);
  border: 1px solid #99f6e4;
  border-radius: 18px;
}
.ai-result-header {
  display: flex;
  gap: 12px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.ai-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
}
.ai-specialty-chip {
  padding: 6px 12px;
  border-radius: 999px;
  background: #fff;
  border: 1px solid #e2e8f0;
  color: #0f172a;
  font-size: 13px;
  font-weight: 700;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
}
.ai-urgency-badge {
  background: #e0f2fe;
  color: #0369a1;
}
.ai-urgency-badge.ai-urgency--critical {
  background: #fee2e2;
  color: #991b1b;
}
.ai-urgency-badge.ai-urgency--high {
  background: #fef3c7;
  color: #92400e;
}
.ai-reasoning-box {
  margin-top: 10px;
  padding-top: 12px;
  border-top: 1px solid #99f6e4;
}
.ai-reasoning-label {
  display: block;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  color: #0d9488;
  margin-bottom: 6px;
}
.ai-reasoning-text {
  margin: 0;
  font-size: 13px;
  color: #0f766e;
  font-style: italic;
}
.empty-state {
  margin-top: 20px;
  padding: 32px 24px;
  text-align: center;
  background: #fff;
  border: 1px solid #fecaca;
  border-radius: 18px;
}
.empty-icon {
  font-size: 48px;
  margin-bottom: 14px;
  display: block;
}
.empty-state h3 {
  margin: 0 0 8px;
  font-size: 19px;
  font-weight: 800;
  color: #991b1b;
}
.empty-state p {
  margin: 0 0 16px;
  font-size: 14px;
  color: #475569;
  line-height: 1.5;
}
.doctors-section {
  margin-top: 28px;
}
.doctors-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 16px;
}
.doctors-header h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 800;
}
.doctors-header p {
  margin: 0;
  font-size: 13px;
  color: #64748b;
}
.doctors-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}
.doctor-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  gap: 16px;
  align-items: center;
  flex-wrap: wrap;
}
.doctor-card:hover {
  border-color: #0d9488;
  transform: translateY(-4px);
  box-shadow: 0 16px 40px rgba(13, 148, 136, 0.14);
}
.doctor-avatar {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: linear-gradient(135deg, #f0fdfa, #ecfdf5);
  color: #0d9488;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 800;
  flex-shrink: 0;
}
.doctor-info {
  flex: 1;
  min-width: 0;
}
.doctor-name {
  font-size: 16px;
  font-weight: 800;
  margin: 0 0 4px;
  color: #0f172a;
}
.doctor-specialty {
  font-size: 13px;
  color: #0d9488;
  font-weight: 700;
  margin: 0 0 10px;
  display: block;
}
.doctor-meta {
  display: flex;
  gap: 6px;
  align-items: center;
  font-size: 12px;
  color: #64748b;
  margin-bottom: 10px;
}
.doctor-divider {
  color: #cbd5e1;
  padding: 0 2px;
}
.doctor-rating-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}
.doctor-rating {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #0f172a;
}
.doctor-rating .star {
  color: #f59e0b;
}
.doctor-fee {
  font-weight: 800;
  color: #0d9488;
  font-size: 14px;
}
.book-btn {
  padding: 10px 18px;
  border: 1px solid #0d9488;
  border-radius: 12px;
  background: #fff;
  color: #0d9488;
  font-weight: 700;
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
  flex-shrink: 0;
}
.book-btn.w-full {
  width: 100%;
  margin-top: 12px;
}
.book-btn:hover {
  background: #0d9488;
  color: #fff;
}
.quick-symptoms {
  margin-top: 30px;
}
.quick-label {
  font-size: 13px;
  color: #64748b;
  margin: 0 0 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.quick-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.quick-chip {
  padding: 10px 18px;
  border: 1px solid #e2e8f0;
  border-radius: 50px;
  background: #fff;
  color: #475569;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.quick-chip:hover {
  border-color: #0d9488;
  color: #0d9488;
  background: #f0fdfa;
  transform: translateY(-1px);
}

.features-section {
  padding: 70px 24px;
  border-top: 1px solid #e2e8f0;
}
.features-container {
  max-width: 1100px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
}
.feature-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  padding: 32px 24px;
  transition: all 0.2s;
}
.feature-card:hover {
  border-color: #0d9488;
  transform: translateY(-3px);
}
.feature-icon {
  font-size: 36px;
  margin-bottom: 16px;
  display: block;
}
.feature-card h3 {
  margin: 0 0 10px;
  font-size: 17px;
  font-weight: 800;
  color: #0f172a;
}
.feature-card p {
  margin: 0;
  font-size: 14px;
  color: #64748b;
  line-height: 1.6;
}
@media (max-width: 900px) {
  .hero-container {
    padding: 0 20px;
  }
  .nav-container {
    padding: 14px 20px;
  }
}
@media (max-width: 600px) {
  .hero-section {
    padding: 50px 16px 30px;
  }
  .search-card {
    padding: 24px;
  }
  .ai-input-actions {
    flex-direction: column;
  }
  .doctors-grid {
    grid-template-columns: 1fr;
  }
  .features-section {
    padding: 40px 16px;
  }
  .feature-card {
    padding: 24px 20px;
  }
}
</style>
