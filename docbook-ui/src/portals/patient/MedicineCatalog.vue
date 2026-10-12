<script setup>
import { ref, onMounted, computed } from 'vue'
import { call } from '../../api'

const medicines = ref([])
const categories = ref([])
const loading = ref(false)
const error = ref(null)
const search = ref('')
const selectedCategory = ref('')
const selectedMedicine = ref(null)
const detailLoading = ref(false)

async function fetchCategories() {
  try {
    const res = await call('docbook.api.medicine.get_medicine_categories')
    categories.value = Array.isArray(res) ? res : []
  } catch {
    // non-fatal
  }
}

async function fetchMedicines() {
  loading.value = true
  error.value = null
  try {
    const res = await call('docbook.api.medicine.list_medicines', {
      search: search.value || null,
      category: selectedCategory.value || null,
    })
    medicines.value = Array.isArray(res) ? res : []
  } catch (e) {
    error.value = e.message || 'Unable to load medicine catalog.'
  } finally {
    loading.value = false
  }
}

async function openDetail(medicine) {
  detailLoading.value = true
  selectedMedicine.value = { ...medicine }
  try {
    const detail = await call('docbook.api.medicine.get_medicine_detail', {
      medicine_name: medicine.name,
    })
    selectedMedicine.value = detail
  } catch (e) {
    // keep what we have
  } finally {
    detailLoading.value = false
  }
}

function closeDetail() {
  selectedMedicine.value = null
}

let debounceTimer = null
function onSearchInput() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(fetchMedicines, 350)
}

function onCategoryChange() {
  fetchMedicines()
}

function categoryColor(cat) {
  const colors = {
    Antibiotic: '#fef3c7',
    Analgesic: '#fce7f3',
    Antiviral: '#dbeafe',
    Antifungal: '#ede9fe',
    Cardiovascular: '#fee2e2',
    Diabetes: '#d1fae5',
    Respiratory: '#e0f2fe',
    Vitamin: '#fef9c3',
    Supplement: '#f3f4f6',
    Other: '#f1f5f9',
  }
  return colors[cat] || '#f1f5f9'
}

function categoryTextColor(cat) {
  const colors = {
    Antibiotic: '#92400e',
    Analgesic: '#9d174d',
    Antiviral: '#1d4ed8',
    Antifungal: '#6d28d9',
    Cardiovascular: '#991b1b',
    Diabetes: '#065f46',
    Respiratory: '#0369a1',
    Vitamin: '#713f12',
    Supplement: '#374151',
    Other: '#475569',
  }
  return colors[cat] || '#475569'
}

onMounted(async () => {
  await fetchCategories()
  await fetchMedicines()
})
</script>

<template>
  <div class="db-page">
    <div class="db-container">
      <!-- Header -->
      <header style="margin-bottom: 28px;">
        <div class="db-eyebrow">HEALTH INFORMATION</div>
        <h1 class="db-page-title">Medicine Catalog</h1>
        <p class="db-section-subtitle">Browse our curated catalog of medicines and health information.</p>
      </header>

      <!-- Search + Filter -->
      <div class="search-bar">
        <div class="search-input-wrap">
          <span class="search-icon">🔍</span>
          <input
            v-model="search"
            @input="onSearchInput"
            type="text"
            class="search-input"
            placeholder="Search by name, generic name or brand…"
          />
          <button v-if="search" class="search-clear" @click="search = ''; fetchMedicines()">✕</button>
        </div>

        <select
          v-model="selectedCategory"
          @change="onCategoryChange"
          class="db-select category-select"
        >
          <option value="">All Categories</option>
          <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
        </select>
      </div>

      <!-- Error -->
      <div v-if="error" class="db-error-panel" style="margin-bottom: 24px;">
        <span style="font-size:18px;">⚠️</span>
        <span>{{ error }}</span>
        <button class="db-btn db-btn--secondary" style="margin-left:auto" @click="fetchMedicines">Retry</button>
      </div>

      <!-- Loading skeleton -->
      <div v-if="loading" class="catalog-grid">
        <div v-for="i in 8" :key="i" class="med-skeleton">
          <div class="db-skeleton" style="height:12px; width:30%; margin-bottom:12px;"></div>
          <div class="db-skeleton" style="height:16px; width:65%; margin-bottom:8px;"></div>
          <div class="db-skeleton" style="height:11px; width:45%; margin-bottom:14px;"></div>
          <div class="db-skeleton" style="height:11px; width:80%;"></div>
        </div>
      </div>

      <!-- Empty state -->
      <div v-else-if="medicines.length === 0" class="db-empty">
        <div class="db-empty-icon" style="font-size:24px;">💊</div>
        <h3>No medicines found</h3>
        <p>Try adjusting your search or category filter.</p>
        <button class="db-btn db-btn--secondary" @click="search = ''; selectedCategory = ''; fetchMedicines()">
          Clear filters
        </button>
      </div>

      <!-- Catalog grid -->
      <div v-else class="catalog-grid">
        <article
          v-for="med in medicines"
          :key="med.name"
          class="med-card"
          @click="openDetail(med)"
        >
          <div class="med-card-top">
            <div
              class="med-category-badge"
              :style="{ background: categoryColor(med.medicine_category), color: categoryTextColor(med.medicine_category) }"
            >
              {{ med.medicine_category || 'Other' }}
            </div>
          </div>

          <div class="med-card-icon">💊</div>

          <div class="med-card-name">{{ med.medicine_name }}</div>
          <div v-if="med.generic_name" class="med-card-generic">{{ med.generic_name }}</div>
          <div v-if="med.brand_name" class="med-card-brand">Brand: {{ med.brand_name }}</div>

          <div class="med-card-pills">
            <span v-if="med.strength" class="med-pill">{{ med.strength }}</span>
            <span v-if="med.dosage_form" class="med-pill">{{ med.dosage_form }}</span>
          </div>

          <div v-if="med.uses" class="med-card-uses">{{ med.uses }}</div>

          <div class="med-card-cta">
            <span>View details →</span>
          </div>
        </article>
      </div>

      <!-- Medicine Detail Modal -->
      <div v-if="selectedMedicine" class="detail-overlay" @click.self="closeDetail">
        <div class="detail-modal">
          <div class="modal-header">
            <div>
              <div
                class="med-category-badge"
                :style="{ background: categoryColor(selectedMedicine.medicine_category), color: categoryTextColor(selectedMedicine.medicine_category) }"
                style="margin-bottom: 12px;"
              >
                {{ selectedMedicine.medicine_category || 'Other' }}
              </div>
              <h2 class="modal-title">{{ selectedMedicine.medicine_name }}</h2>
              <div v-if="selectedMedicine.generic_name" class="modal-subtitle">
                Generic: <strong>{{ selectedMedicine.generic_name }}</strong>
              </div>
              <div v-if="selectedMedicine.brand_name" class="modal-subtitle">
                Brand: {{ selectedMedicine.brand_name }}
              </div>
            </div>
            <button class="close-btn" @click="closeDetail">✕</button>
          </div>

          <div v-if="detailLoading" style="padding: 16px 0;">
            <div class="db-skeleton" style="height:13px; width:70%; margin-bottom:10px;"></div>
            <div class="db-skeleton" style="height:13px; width:85%; margin-bottom:10px;"></div>
            <div class="db-skeleton" style="height:13px; width:55%;"></div>
          </div>

          <div v-else>
            <!-- Properties -->
            <div class="modal-props">
              <div v-if="selectedMedicine.strength" class="modal-prop">
                <span class="prop-label">Strength</span>
                <span class="prop-value">{{ selectedMedicine.strength }}</span>
              </div>
              <div v-if="selectedMedicine.dosage_form" class="modal-prop">
                <span class="prop-label">Form</span>
                <span class="prop-value">{{ selectedMedicine.dosage_form }}</span>
              </div>
            </div>

            <div class="modal-sections">
              <div v-if="selectedMedicine.description" class="modal-section">
                <div class="modal-section-title">About</div>
                <p class="modal-section-text">{{ selectedMedicine.description }}</p>
              </div>

              <div v-if="selectedMedicine.uses" class="modal-section">
                <div class="modal-section-title">Uses</div>
                <p class="modal-section-text">{{ selectedMedicine.uses }}</p>
              </div>

              <div v-if="selectedMedicine.how_it_works" class="modal-section">
                <div class="modal-section-title">How It Works</div>
                <p class="modal-section-text">{{ selectedMedicine.how_it_works }}</p>
              </div>

              <div v-if="selectedMedicine.common_side_effects" class="modal-section modal-section--warning">
                <div class="modal-section-title">⚠️ Common Side Effects</div>
                <p class="modal-section-text">{{ selectedMedicine.common_side_effects }}</p>
              </div>

              <div v-if="selectedMedicine.precautions" class="modal-section modal-section--caution">
                <div class="modal-section-title">🔴 Precautions</div>
                <p class="modal-section-text">{{ selectedMedicine.precautions }}</p>
              </div>

              <div v-if="selectedMedicine.storage_instructions" class="modal-section">
                <div class="modal-section-title">Storage</div>
                <p class="modal-section-text">{{ selectedMedicine.storage_instructions }}</p>
              </div>
            </div>

            <div class="modal-disclaimer">
              ⚠️ This information is for general awareness only. Always follow your doctor's prescription and do not self-medicate.
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Search bar */
.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.search-input-wrap {
  flex: 1;
  min-width: 200px;
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 12px;
  font-size: 15px;
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 10px 38px 10px 38px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  font-family: var(--db-font);
  font-size: 14px;
  color: #0f172a;
  background: white;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.search-input:focus {
  border-color: #0d9488;
  box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.12);
}

.search-clear {
  position: absolute;
  right: 10px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 13px;
  color: #94a3b8;
}

.category-select {
  min-width: 180px;
  flex-shrink: 0;
}

/* Catalog grid */
.catalog-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 18px;
}

.med-skeleton {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 20px;
  min-height: 180px;
}

.med-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 20px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.med-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.10);
  border-color: #99f6e4;
}

.med-card-top {
  margin-bottom: 12px;
}

.med-category-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.6px;
  text-transform: uppercase;
}

.med-card-icon {
  font-size: 28px;
  margin-bottom: 12px;
}

.med-card-name {
  font-size: 16px;
  font-weight: 800;
  color: #0f172a;
  margin-bottom: 3px;
  line-height: 1.3;
}

.med-card-generic {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 2px;
}

.med-card-brand {
  font-size: 11px;
  color: #94a3b8;
  margin-bottom: 10px;
}

.med-card-pills {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.med-pill {
  padding: 2px 9px;
  background: #f1f5f9;
  border-radius: 999px;
  font-size: 11px;
  color: #475569;
  font-weight: 600;
}

.med-card-uses {
  font-size: 12px;
  color: #64748b;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 12px;
  flex: 1;
}

.med-card-cta {
  font-size: 12px;
  font-weight: 700;
  color: #0d9488;
  margin-top: auto;
}

/* Modal */
.detail-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(6px);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.detail-modal {
  background: white;
  border-radius: 20px;
  width: 580px;
  max-width: 100%;
  max-height: 85vh;
  overflow-y: auto;
  padding: 32px;
  box-shadow: 0 24px 64px rgba(15, 23, 42, 0.18);
  animation: popIn 0.2s cubic-bezier(0.22, 1, 0.36, 1);
}

@keyframes popIn {
  from { transform: scale(0.94); opacity: 0; }
  to   { transform: scale(1);    opacity: 1; }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 20px;
}

.modal-title {
  font-size: 24px;
  font-weight: 800;
  color: #0f172a;
  margin: 0 0 6px;
  letter-spacing: -0.5px;
}

.modal-subtitle {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 2px;
}

.close-btn {
  width: 34px;
  height: 34px;
  background: #f1f5f9;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #64748b;
}

.close-btn:hover {
  background: #e2e8f0;
}

.modal-props {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 20px;
}

.modal-prop {
  display: flex;
  flex-direction: column;
  padding: 10px 16px;
  background: #f8fafc;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  gap: 2px;
}

.prop-label {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: #94a3b8;
}

.prop-value {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.modal-sections {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.modal-section {
  padding: 14px 16px;
  background: #f8fafc;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
}

.modal-section--warning {
  background: #fffbeb;
  border-color: #fde68a;
}

.modal-section--caution {
  background: #fef2f2;
  border-color: #fecaca;
}

.modal-section-title {
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #94a3b8;
  margin-bottom: 6px;
}

.modal-section--warning .modal-section-title { color: #b45309; }
.modal-section--caution .modal-section-title { color: #991b1b; }

.modal-section-text {
  font-size: 13px;
  color: #334155;
  line-height: 1.6;
  margin: 0;
}

.modal-disclaimer {
  margin-top: 20px;
  padding: 12px 16px;
  background: #f8fafc;
  border-radius: 8px;
  font-size: 11px;
  color: #94a3b8;
  border: 1px solid #e2e8f0;
}

@media (max-width: 640px) {
  .search-bar { flex-direction: column; }
  .catalog-grid { grid-template-columns: 1fr; }
  .detail-modal { padding: 20px; }
}
</style>
