<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import jsQR from 'jsqr'
import { call } from '../../api'

const router = useRouter()

const checkinMode = ref('camera') // 'camera' | 'upload' | 'manual'
const checkingIn = ref(false)
const checkinError = ref(null)
const checkinSuccess = ref(null)

// Manual Entry
const manualInput = ref('')

// Camera Scanner
const videoRef = ref(null)
const canvasRef = ref(null)
const cameraActive = ref(false)
const cameraError = ref(null)
let streamInstance = null
let animationFrameId = null

// Upload Mode
const uploadedPreview = ref(null)
const uploadProcessing = ref(false)

// Today's pending check-in list for quick arrival
const todayPending = ref([])
const pendingLoading = ref(false)

async function fetchTodayPending() {
  pendingLoading.value = true
  try {
    const today = new Date().toISOString().slice(0, 10)
    const res = await call('docbook.api.queue.get_receptionist_dashboard', { date: today })
    const all = Array.isArray(res?.appointments) ? res.appointments : []
    todayPending.value = all.filter(a => !a.checked_in && a.status !== 'Completed' && a.status !== 'Cancelled')
  } catch (err) {
    console.warn('Failed to load pending appointments:', err)
  } finally {
    pendingLoading.value = false
  }
}

async function processCheckin(rawPayload) {
  if (!rawPayload || !rawPayload.trim()) {
    checkinError.value = 'Please provide a valid QR pass or appointment number.'
    return
  }

  checkingIn.value = true
  checkinError.value = null
  checkinSuccess.value = null

  try {
    const payload = rawPayload.trim()
    const res = await call('docbook.api.queue.join_queue_from_qr', {
      qr_data: payload,
      appointment_id: payload.startsWith('DOCBOOK|APT|') ? undefined : payload,
    })

    if (res?.success) {
      checkinSuccess.value = {
        token: res.token,
        appointment: res.appointment,
        patient: res.patient,
        doctor: res.doctor,
        queue_position: res.queue_position || 1,
        visit_stage: res.visit_stage || 'Waiting',
        fast_track: res.fast_track,
      }
      stopCamera()
      fetchTodayPending()
      playBeep()
    } else {
      checkinError.value = res?.message || 'Check-in failed. Please verify details.'
    }
  } catch (err) {
    checkinError.value = err.message || 'Check-in failed. Patient may already be checked in.'
  } finally {
    checkingIn.value = false
  }
}

function playBeep() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.type = 'sine'
    osc.frequency.setValueAtTime(880, ctx.currentTime)
    gain.gain.setValueAtTime(0.2, ctx.currentTime)
    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.start()
    osc.stop(ctx.currentTime + 0.18)
  } catch (e) {
    // Audio not allowed / muted
  }
}

// -------------------------------------------------------------
// Mode 1: Camera Scanner
// -------------------------------------------------------------
async function startCamera() {
  cameraError.value = null
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    cameraError.value = 'Camera not supported in this browser. Please use Upload or Manual mode.'
    return
  }
  try {
    streamInstance = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } }
    })
    if (videoRef.value) {
      videoRef.value.srcObject = streamInstance
      videoRef.value.setAttribute('playsinline', 'true')
      await videoRef.value.play()
      cameraActive.value = true
      scanCameraFrame()
    }
  } catch (err) {
    cameraError.value = 'Camera access denied or unavailable. You can use Upload QR or Manual entry.'
    cameraActive.value = false
  }
}

function stopCamera() {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
    animationFrameId = null
  }
  if (streamInstance) {
    streamInstance.getTracks().forEach(t => t.stop())
    streamInstance = null
  }
  cameraActive.value = false
}

function scanCameraFrame() {
  if (!cameraActive.value || !videoRef.value || !canvasRef.value) return
  const video = videoRef.value
  const canvas = canvasRef.value

  if (video.readyState === video.HAVE_ENOUGH_DATA) {
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
    const code = jsQR(imageData.data, imageData.width, imageData.height, {
      inversionAttempts: 'dontInvert',
    })

    if (code && code.data) {
      // Detected QR Code!
      processCheckin(code.data)
      return
    }
  }

  animationFrameId = requestAnimationFrame(scanCameraFrame)
}

// -------------------------------------------------------------
// Mode 2: Upload QR Image
// -------------------------------------------------------------
function onFileSelect(e) {
  const file = e.target.files?.[0]
  if (!file) return
  uploadProcessing.value = true
  checkinError.value = null

  const reader = new FileReader()
  reader.onload = (ev) => {
    uploadedPreview.value = ev.target.result
    const img = new Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = img.naturalWidth
      canvas.height = img.naturalHeight
      const ctx = canvas.getContext('2d')
      ctx.drawImage(img, 0, 0)
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
      const code = jsQR(imageData.data, imageData.width, imageData.height)

      uploadProcessing.value = false
      if (code && code.data) {
        processCheckin(code.data)
      } else {
        checkinError.value = 'Could not detect a valid QR pass in this image. Please ensure the QR code is clearly visible.'
      }
    }
    img.src = ev.target.result
  }
  reader.readAsDataURL(file)
}

function switchMode(mode) {
  checkinMode.value = mode
  checkinError.value = null
  if (mode === 'camera') {
    startCamera()
  } else {
    stopCamera()
  }
}

function resetCheckin() {
  checkinSuccess.value = null
  checkinError.value = null
  manualInput.value = ''
  uploadedPreview.value = null
  if (checkinMode.value === 'camera') {
    startCamera()
  }
}

onMounted(() => {
  fetchTodayPending()
  if (checkinMode.value === 'camera') {
    startCamera()
  }
})

onUnmounted(() => {
  stopCamera()
})
</script>

<template>
  <main class="rec-checkin-page">
    <div class="kiosk-shell">

      <!-- Header -->
      <header class="kiosk-head">
        <div class="kiosk-badge">HOSPITAL ARRIVAL &amp; CHECK-IN STATION</div>
        <h1>Patient Self &amp; Desk Check-in<span>.</span></h1>
        <p class="kiosk-sub">
          Scan QR code, upload pass, or enter appointment number to check in, receive token #, and notify doctor.
        </p>
      </header>

      <!-- SUCCESS CONFIRMATION MODAL / CARD -->
      <div v-if="checkinSuccess" class="success-card">
        <div class="success-icon-bubble">✓</div>
        <h2>Checked In Successfully!</h2>
        <p class="success-sub">
          Patient arrival registered and updated to Patient Portal &amp; Doctor Live Queue.
        </p>

        <!-- Big Token Display -->
        <div class="token-display-box">
          <span class="token-label">YOUR QUEUE TOKEN</span>
          <div class="token-number">#{{ checkinSuccess.token }}</div>
          <span class="token-stage">Stage: {{ checkinSuccess.visit_stage }} · Position in Queue: #{{ checkinSuccess.queue_position }}</span>
        </div>

        <div class="success-meta-grid">
          <div class="meta-item">
            <span class="meta-label">Appointment</span>
            <strong class="meta-val">#{{ checkinSuccess.appointment }}</strong>
          </div>
          <div class="meta-item">
            <span class="meta-label">Patient</span>
            <strong class="meta-val">{{ checkinSuccess.patient }}</strong>
          </div>
          <div class="meta-item">
            <span class="meta-label">Consulting Doctor</span>
            <strong class="meta-val">Dr. {{ checkinSuccess.doctor }}</strong>
          </div>
        </div>

        <div class="success-actions">
          <button class="btn-primary" @click="resetCheckin">
            Scan Next Patient →
          </button>
          <button class="btn-secondary" @click="router.push('/receptionist')">
            View Today's Queue
          </button>
        </div>
      </div>

      <!-- MAIN SCANNER CONTAINER -->
      <div v-else class="kiosk-body">

        <!-- Mode Selector Tabs (3 Options) -->
        <div class="mode-tabs">
          <button
            class="mode-btn"
            :class="{ active: checkinMode === 'camera' }"
            @click="switchMode('camera')"
          >
            📷 1. Live Camera Scan
          </button>
          <button
            class="mode-btn"
            :class="{ active: checkinMode === 'upload' }"
            @click="switchMode('upload')"
          >
            🖼️ 2. Upload QR Image
          </button>
          <button
            class="mode-btn"
            :class="{ active: checkinMode === 'manual' }"
            @click="switchMode('manual')"
          >
            ⌨️ 3. Appointment # Entry
          </button>
        </div>

        <!-- ERROR BANNER -->
        <div v-if="checkinError" class="error-strip">
          <span>⚠️</span>
          <div class="flex-1">{{ checkinError }}</div>
          <button class="err-close" @click="checkinError = null">✕</button>
        </div>

        <!-- OPTION 1: LIVE CAMERA QR SCANNER -->
        <section v-if="checkinMode === 'camera'" class="scanner-card">
          <div class="camera-stage">
            <video ref="videoRef" class="camera-video" autoplay playsinline muted></video>
            <canvas ref="canvasRef" style="display: none;"></canvas>

            <!-- Target Reticle Overlay -->
            <div class="scanner-reticle">
              <div class="corner-tl"></div>
              <div class="corner-tr"></div>
              <div class="corner-bl"></div>
              <div class="corner-br"></div>
              <div class="scan-laser"></div>
            </div>

            <div v-if="cameraError" class="camera-error-overlay">
              <span>📷</span>
              <p>{{ cameraError }}</p>
              <button class="btn-secondary" @click="startCamera">Try Again</button>
            </div>

            <div v-if="checkingIn" class="checking-overlay">
              <div class="spinner"></div>
              <p>Checking in patient…</p>
            </div>
          </div>

          <div class="scanner-hints">
            <p>Position the patient's QR code pass inside the target frame above.</p>
            <span class="auto-scan-badge">⚡ Real-time automatic scanner active</span>
          </div>
        </section>

        <!-- OPTION 2: UPLOAD QR PASS -->
        <section v-if="checkinMode === 'upload'" class="scanner-card">
          <div class="upload-dropzone">
            <input
              type="file"
              accept="image/*"
              class="hidden-file-input"
              id="qrFileInput"
              @change="onFileSelect"
            />
            <label for="qrFileInput" class="dropzone-label">
              <div v-if="uploadProcessing" class="upload-loading">
                <div class="spinner"></div>
                <p>Analyzing QR image…</p>
              </div>
              <template v-else>
                <div class="drop-icon">📤</div>
                <h3>Click to Select or Drop QR Pass</h3>
                <p class="drop-sub">Upload the downloaded QR pass image (PNG, JPG, WebP)</p>
                <span class="btn-choose">Choose Image File</span>
              </template>
            </label>
          </div>

          <div v-if="uploadedPreview" class="preview-box">
            <p class="text-xs text-slate-500">Uploaded File Preview:</p>
            <img :src="uploadedPreview" alt="QR Preview" class="preview-thumb" />
          </div>
        </section>

        <!-- OPTION 3: MANUAL ENTRY WITH APPOINTMENT NUMBER -->
        <section v-if="checkinMode === 'manual'" class="scanner-card">
          <div class="manual-form">
            <label class="form-label">Appointment ID / Token Number:</label>
            <div class="manual-input-row">
              <input
                v-model="manualInput"
                type="text"
                class="manual-input"
                placeholder="e.g. APT-00008 or token"
                autofocus
                @keyup.enter="processCheckin(manualInput)"
              />
              <button
                class="btn-primary"
                :disabled="checkingIn || !manualInput.trim()"
                @click="processCheckin(manualInput)"
              >
                {{ checkingIn ? 'Checking In…' : 'Check In Patient →' }}
              </button>
            </div>
            <p class="form-hint">
              Enter the patient's appointment reference (e.g. <code>APT-00008</code>) from their booking confirmation or SMS.
            </p>
          </div>

          <!-- Quick 1-Click Pending Arrivals List -->
          <div class="quick-pending-section">
            <h4 class="quick-title">Today's Expected Patients (Click to Check In)</h4>
            <div v-if="pendingLoading" class="text-xs text-slate-400">Loading today's arrivals…</div>
            <div v-else-if="!todayPending.length" class="text-xs text-slate-500">
              All scheduled patients for today are already checked in.
            </div>
            <div v-else class="pending-chips-grid">
              <button
                v-for="p in todayPending"
                :key="p.name"
                class="pending-patient-btn"
                :disabled="checkingIn"
                @click="processCheckin(p.name)"
              >
                <div class="p-name">{{ p.patient_name || p.patient }}</div>
                <div class="p-sub">#{{ p.name }} · Dr. {{ p.doctor_name || p.doctor }}</div>
                <span class="p-action">✓ Check In</span>
              </button>
            </div>
          </div>
        </section>

      </div>

    </div>
  </main>
</template>

<style scoped>
.rec-checkin-page {
  min-height: 100vh;
  background: #f8fafc;
  color: #0f172a;
  padding: 40px 24px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
.kiosk-shell {
  max-width: 860px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
}
.kiosk-head { text-align: center; }
.kiosk-badge {
  display: inline-block;
  background: #ccfbf1;
  color: #0f766e;
  border: 1px solid #99f6e4;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.1em;
  padding: 4px 12px;
  border-radius: 20px;
  text-transform: uppercase;
  margin-bottom: 8px;
}
.kiosk-head h1 {
  font-size: 32px;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
  letter-spacing: -0.02em;
}
.kiosk-head h1 span { color: #0d9488; }
.kiosk-sub { color: #64748b; font-size: 14px; margin: 8px 0 0; }

/* Mode Tabs */
.mode-tabs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  background: #ffffff;
  padding: 6px;
  border-radius: 14px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 2px 8px rgba(0,0,0,0.03);
}
@media (max-width: 600px) {
  .mode-tabs { grid-template-columns: 1fr; }
}
.mode-btn {
  background: transparent;
  color: #64748b;
  border: none;
  border-radius: 10px;
  padding: 12px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
}
.mode-btn:hover { color: #0f172a; background: #f1f5f9; }
.mode-btn.active {
  background: #0d9488;
  color: #ffffff;
  box-shadow: 0 4px 12px rgba(13,148,136,0.25);
}

/* Error Strip */
.error-strip {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
  border-radius: 12px;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
}
.err-close { background: none; border: none; color: #b91c1c; cursor: pointer; }

/* Scanner Card */
.scanner-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.04);
}

/* Camera Stage */
.camera-stage {
  position: relative;
  width: 100%;
  height: 380px;
  background: #0f172a;
  border-radius: 14px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}
.camera-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.scanner-reticle {
  position: absolute;
  width: 220px;
  height: 220px;
  border: 2px dashed rgba(255,255,255,0.4);
  border-radius: 16px;
  pointer-events: none;
}
.corner-tl, .corner-tr, .corner-bl, .corner-br {
  position: absolute;
  width: 20px;
  height: 20px;
  border-color: #10b981;
  border-style: solid;
}
.corner-tl { top: -2px; left: -2px; border-width: 4px 0 0 4px; border-top-left-radius: 8px; }
.corner-tr { top: -2px; right: -2px; border-width: 4px 4px 0 0; border-top-right-radius: 8px; }
.corner-bl { bottom: -2px; left: -2px; border-width: 0 0 4px 4px; border-bottom-left-radius: 8px; }
.corner-br { bottom: -2px; right: -2px; border-width: 0 4px 4px 0; border-bottom-right-radius: 8px; }

.scan-laser {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background: #10b981;
  box-shadow: 0 0 10px #10b981, 0 0 20px #10b981;
  animation: scan-bounce 2.2s ease-in-out infinite alternate;
}
@keyframes scan-bounce {
  0% { top: 0; }
  100% { top: 100%; }
}

.camera-error-overlay, .checking-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.94);
  color: #0f172a;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 24px;
  text-align: center;
}
.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid rgba(13, 148, 136, 0.2);
  border-top-color: #0d9488;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.scanner-hints {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.scanner-hints p { color: #64748b; font-size: 13px; margin: 0; }
.auto-scan-badge {
  font-size: 11px;
  color: #0f766e;
  background: #ccfbf1;
  border: 1px solid #99f6e4;
  padding: 4px 10px;
  border-radius: 12px;
  font-weight: 700;
}

/* Upload Mode */
.upload-dropzone {
  border: 2px dashed #cbd5e1;
  border-radius: 16px;
  padding: 48px 24px;
  text-align: center;
  background: #f8fafc;
  cursor: pointer;
  transition: all 0.2s;
}
.upload-dropzone:hover { border-color: #0d9488; background: #f0fdfa; }
.hidden-file-input { display: none; }
.dropzone-label { cursor: pointer; display: flex; flex-direction: column; align-items: center; gap: 10px; }
.drop-icon { font-size: 48px; }
.dropzone-label h3 { margin: 0; font-size: 18px; font-weight: 700; color: #0f172a; }
.drop-sub { color: #64748b; font-size: 13px; margin: 0; }
.btn-choose {
  background: #0d9488;
  color: #ffffff;
  padding: 8px 18px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 700;
  margin-top: 8px;
  display: inline-block;
  transition: background 0.15s;
}
.btn-choose:hover { background: #0f766e; }
.preview-box { text-align: center; }
.preview-thumb { max-width: 200px; border-radius: 10px; border: 1px solid #e2e8f0; margin-top: 6px; }

/* Manual Mode */
.manual-form { display: flex; flex-direction: column; gap: 8px; }
.form-label { font-size: 13px; font-weight: 700; color: #334155; }
.manual-input-row { display: flex; gap: 10px; flex-wrap: wrap; }
.manual-input {
  flex: 1;
  min-width: 240px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 12px 16px;
  color: #0f172a;
  font-size: 16px;
  font-weight: 600;
  outline: none;
  transition: border-color 0.15s;
}
.manual-input:focus { border-color: #0d9488; box-shadow: 0 0 0 3px rgba(13,148,136,0.15); }
.form-hint { color: #64748b; font-size: 12px; margin: 4px 0 0; }

.quick-pending-section {
  border-top: 1px solid #e2e8f0;
  padding-top: 16px;
  margin-top: 8px;
}
.quick-title { font-size: 13px; font-weight: 800; color: #475569; text-transform: uppercase; margin: 0 0 10px; }
.pending-chips-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 8px;
}
.pending-patient-btn {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 12px;
  text-align: left;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 2px;
  transition: all 0.15s;
}
.pending-patient-btn:hover { border-color: #0d9488; background: #f0fdfa; }
.p-name { font-weight: 700; font-size: 13px; color: #0f172a; }
.p-sub { font-size: 11px; color: #64748b; }
.p-action { font-size: 11px; font-weight: 800; color: #0d9488; margin-top: 4px; }

/* Success Card */
.success-card {
  background: #ffffff;
  border: 2px solid #0d9488;
  border-radius: 20px;
  padding: 40px 24px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  box-shadow: 0 10px 30px rgba(13,148,136,0.08);
}
.success-icon-bubble {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: #0d9488;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  font-weight: 900;
  box-shadow: 0 4px 16px rgba(13,148,136,0.3);
}
.success-card h2 { font-size: 26px; font-weight: 800; color: #0f172a; margin: 0; }
.success-sub { color: #64748b; font-size: 14px; margin: 0; }

.token-display-box {
  background: #f0fdfa;
  border: 1px solid #99f6e4;
  border-radius: 16px;
  padding: 20px 32px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  margin: 8px 0;
}
.token-label { font-size: 11px; font-weight: 800; color: #0f766e; letter-spacing: 0.1em; }
.token-number { font-size: 52px; font-weight: 900; color: #0d9488; line-height: 1; margin: 6px 0; }
.token-stage { font-size: 13px; font-weight: 600; color: #134e4a; }

.success-meta-grid {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  justify-content: center;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  padding: 12px 20px;
  border-radius: 12px;
}
.meta-item { display: flex; flex-direction: column; gap: 2px; text-align: center; }
.meta-label { font-size: 10px; font-weight: 700; color: #64748b; text-transform: uppercase; }
.meta-val { font-size: 14px; font-weight: 700; color: #0f172a; }

.success-actions { display: flex; gap: 12px; margin-top: 12px; flex-wrap: wrap; justify-content: center; }
.btn-primary {
  background: #0d9488;
  color: #ffffff;
  border: none;
  border-radius: 10px;
  padding: 12px 24px;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.15s;
}
.btn-primary:hover { background: #0f766e; box-shadow: 0 4px 12px rgba(13,148,136,0.25); }
.btn-secondary {
  background: #ffffff;
  color: #475569;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px 20px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s;
}
.btn-secondary:hover { background: #f8fafc; color: #0f172a; }
</style>
