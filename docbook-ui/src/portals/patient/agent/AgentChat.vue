<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { call } from '../../../api'
import { useAuthStore } from '../../../stores/auth'

const auth = useAuthStore()

// ---------------------------------------------------------------
// State
// ---------------------------------------------------------------
const open = ref(false)
const messages = ref([])   // { role: 'user' | 'assistant', content }
const input = ref('')
const sending = ref(false)
const loadingHistory = ref(false)
const messagesEl = ref(null)

const starterPrompts = [
  'What appointments do I have coming up?',
  'Show my prescriptions',
  'Find me a dentist',
  'Help me book an appointment',
]

// Only patients see the assistant.
// NOTE: the backend `get_current_user` returns a singular `role` string
// ("Patient" / "Doctor" / "User"); some flows may provide a `roles` array.
// Check both so the FAB actually renders for patients.
const canUseAgent = computed(() => {
  if (!auth.isLoggedIn || !auth.user) return false

  const rolesArr = auth.user.roles || []
  const names = rolesArr
    .map((r) => (typeof r === 'string' ? r : r?.role || ''))
    .filter(Boolean)
    .map((r) => r.toLowerCase())

  const single = (auth.user.role || '').toLowerCase()

  return names.includes('patient') || single === 'patient'
})

// ---------------------------------------------------------------
// Markdown rendering (safe)
// ---------------------------------------------------------------
function renderMarkdown(text) {
  if (!text) return ''
  const raw = marked.parse(text, { breaks: true, gfm: true })
  return DOMPurify.sanitize(raw)
}

// ---------------------------------------------------------------
// Data
// ---------------------------------------------------------------
async function loadHistory() {
  loadingHistory.value = true
  try {
    const rows = await call('docbook.api.agent.get_history', {}, { quiet: true })
    messages.value = Array.isArray(rows) ? rows.map((r) => ({ role: r.role, content: r.content })) : []
    scrollToBottom()
  } catch (e) {
    // Non-fatal: just start fresh.
    messages.value = []
  } finally {
    loadingHistory.value = false
  }
}

async function send(text) {
  const content = (text ?? input.value).trim()
  if (!content || sending.value) return

  input.value = ''
  messages.value.push({ role: 'user', content })
  console.log(`[AgentChat] user message: ${content}`)
  // Bound in-memory thread size — history is persisted server-side and
  // reloaded via loadHistory(), so dropping old local rows is safe.
  if (messages.value.length > 200) {
    messages.value.splice(0, messages.value.length - 200)
  }
  sending.value = true
  scrollToBottom()

  // Optimistic assistant placeholder for the typing indicator.
  const pendingIndex = messages.value.push({ role: 'assistant', content: '', pending: true }) - 1
  scrollToBottom()

  try {
    const res = await call('docbook.api.agent.chat', { message: content }, { quiet: true })
    const reply = res?.reply || "I'm sorry, I couldn't generate a response."
    messages.value[pendingIndex] = { role: 'assistant', content: reply }
  } catch (e) {
    // Surface the real backend message (e.g. "AI assistant is not
    // configured") when available, so users aren't left guessing.
    // On network failure the optimistic rows are dropped and history
    // is reloaded, so a retried send can't duplicate rows.
    const detail = e?.message || 'Please try again in a moment.'
    messages.value.splice(pendingIndex, 1)
    messages.value.push({
      role: 'assistant',
      content: `⚠️ ${detail}`,
    })
    try {
      const rows = await call('docbook.api.agent.get_history', {}, { quiet: true })
      if (Array.isArray(rows)) {
        messages.value = rows.map((r) => ({ role: r.role, content: r.content }))
        // Re-append the failed user message context if the server never
        // persisted it (network died before insert), so the thread reads
        // correctly and the user can retry by sending again.
        const last = messages.value[messages.value.length - 1]
        if (!last || !(last.role === 'user' && last.content === content)) {
          messages.value.push({ role: 'user', content })
          messages.value.push({
            role: 'assistant',
            content: `⚠️ ${detail}`,
          })
        }
      }
    } catch {
      // Reload is best-effort; the inline error row stays.
    }
  } finally {
    sending.value = false
    scrollToBottom()
  }
}

async function clearChat() {
  try {
    await call('docbook.api.agent.clear_history', {}, { quiet: true })
  } catch {
    // ignore
  }
  messages.value = []
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesEl.value) {
      messagesEl.value.scrollTop = messagesEl.value.scrollHeight
    }
  })
}

function toggleOpen() {
  open.value = !open.value
  if (open.value) {
    if (!messages.value.length) loadHistory()
    nextTick(() => input.value && document.activeElement?.blur())
  }
}

function onKeydown(e) {
  // Ignore Enter while an IME candidate window is open (CJK input), so
  // composition confirmation doesn't send the message prematurely.
  if (e.isComposing || e.keyCode === 229) return
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

// Close on Escape
function onDocKey(e) {
  if (e.key === 'Escape' && open.value) open.value = false
}

onMounted(() => {
  document.addEventListener('keydown', onDocKey)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onDocKey)
})

watch(open, (v) => {
  if (v) nextTick(scrollToBottom)
})

// Reset local thread when the account changes (login / logout / switch),
// so the previous user's messages never flash for the next user.
watch(
  () => auth.user?.user || auth.user?.email || null,
  () => {
    open.value = false
    input.value = ''
    sending.value = false
    messages.value = []
  }
)
</script>

<template>
  <!-- Floating launcher (bottom-right) — patients only -->
  <button
    v-if="canUseAgent"
    class="agent-fab"
    :class="{ 'agent-fab--active': open }"
    type="button"
    :aria-label="open ? 'Close health assistant' : 'Open health assistant'"
    @click="toggleOpen"
  >
    <span v-if="!open" class="agent-fab-icon">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/>
        <path d="M2 14h2M20 14h2M15 13v2M9 13v2"/>
      </svg>
      <span class="agent-fab-pulse"></span>
    </span>
    <svg v-else class="agent-fab-close" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
      <path d="M18 6 6 18M6 6l12 12"/>
    </svg>
    <span class="agent-fab-label">Health Assistant</span>
  </button>

  <!-- Chat panel -->
  <transition name="agent-pop">
    <section v-if="canUseAgent && open" class="agent-panel" role="dialog" aria-label="DocBook health assistant">
      <!-- Header -->
      <header class="agent-head">
        <div class="agent-head-avatar">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/>
            <path d="M2 14h2M20 14h2M15 13v2M9 13v2"/>
          </svg>
          <span class="agent-head-status"></span>
        </div>
        <div class="agent-head-copy">
          <h2>DocBook Assistant</h2>
          <p>Ask about appointments, doctors &amp; prescriptions</p>
        </div>
        <button class="agent-head-clear" type="button" title="Clear chat" @click="clearChat">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
          </svg>
        </button>
        <button class="agent-head-close" type="button" aria-label="Close" @click="open = false">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M18 6 6 18M6 6l12 12"/>
          </svg>
        </button>
      </header>


      <!-- Messages -->
      <div ref="messagesEl" class="agent-body">
        <!-- Welcome / empty state -->
        <div v-if="!messages.length && !loadingHistory" class="agent-welcome">
          <div class="agent-welcome-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/>
              <path d="M2 14h2M20 14h2M15 13v2M9 13v2"/>
            </svg>
          </div>
          <h3>Hi! I'm your DocBook assistant 👋</h3>
          <p>I can help you check appointments, find doctors, view prescriptions, and book visits — using only your own health data.</p>
          <div class="agent-suggestions">
            <button
              v-for="s in starterPrompts"
              :key="s"
              class="agent-suggestion"
              type="button"
              @click="send(s)"
            >
              {{ s }}
            </button>
          </div>
        </div>

        <!-- Loading history -->
        <div v-else-if="loadingHistory" class="agent-typing">
          <span></span><span></span><span></span>
        </div>

        <!-- Message thread -->
        <template v-else>
          <div
            v-for="(m, i) in messages"
            :key="i"
            class="agent-msg"
            :class="m.role === 'user' ? 'agent-msg--user' : 'agent-msg--bot'"
          >
            <div v-if="m.role !== 'user'" class="agent-msg-avatar">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/>
                <path d="M2 14h2M20 14h2M15 13v2M9 13v2"/>
              </svg>
            </div>
            <div class="agent-bubble">
              <div v-if="m.pending" class="agent-typing"><span></span><span></span><span></span></div>
              <div v-else class="agent-markdown" v-html="renderMarkdown(m.content)"></div>
            </div>
          </div>
        </template>
      </div>

      <!-- Input -->
      <footer class="agent-input">
        <textarea
          v-model="input"
          rows="1"
          class="agent-textarea"
          placeholder="Type your health question…"
          @keydown="onKeydown"
        ></textarea>
        <button
          class="agent-send"
          type="button"
          :disabled="sending || !input.trim()"
          aria-label="Send message"
          @click="send()"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/>
          </svg>
        </button>
      </footer>
    </section>
  </transition>
</template>


<style scoped>
/* ============================================================
   Floating launcher button
   ============================================================ */
.agent-fab {
  position: fixed;
  right: 22px;
  bottom: 22px;
  z-index: 900;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  height: 54px;
  padding: 0 20px 0 16px;
  border: none;
  border-radius: 999px;
  background: linear-gradient(120deg, #0d9488, #0e7490);
  color: #fff;
  font-family: inherit;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 12px 30px rgba(13, 148, 136, 0.4);
  transition: transform 0.15s, box-shadow 0.15s;
}
.agent-fab:hover { transform: translateY(-2px); box-shadow: 0 16px 38px rgba(13, 148, 136, 0.5); }
.agent-fab:active { transform: scale(0.97); }
.agent-fab--active { padding: 0 16px; box-shadow: 0 8px 20px rgba(13, 118, 110, 0.4); }

.agent-fab-icon { position: relative; display: flex; }
.agent-fab-icon svg { width: 24px; height: 24px; }
.agent-fab-close { width: 24px; height: 24px; }

.agent-fab-pulse {
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  border: 2px solid rgba(94, 234, 212, 0.7);
  animation: agent-ping 2s cubic-bezier(0, 0, 0.2, 1) infinite;
}
@keyframes agent-ping {
  0% { transform: scale(0.8); opacity: 0.8; }
  80%, 100% { transform: scale(1.6); opacity: 0; }
}

/* ============================================================
   Chat panel
   ============================================================ */
.agent-panel {
  position: fixed;
  right: 22px;
  bottom: 88px;
  z-index: 901;
  width: 380px;
  max-width: calc(100vw - 32px);
  height: 560px;
  max-height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 20px;
  border: 1px solid #e8eef5;
  box-shadow: 0 24px 64px rgba(15, 23, 42, 0.22);
  overflow: hidden;
}

/* Transition */
.agent-pop-enter-active, .agent-pop-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.agent-pop-enter-from, .agent-pop-leave-to { opacity: 0; transform: translateY(16px) scale(0.98); }

/* ---------- Header ---------- */
.agent-head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: linear-gradient(120deg, #0f766e, #0d9488);
  color: #fff;
}

.agent-head-avatar {
  position: relative;
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.28);
}
.agent-head-avatar svg { width: 22px; height: 22px; }

.agent-head-status {
  position: absolute;
  right: -2px;
  bottom: -2px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #34d399;
  border: 2px solid #0d9488;
}

.agent-head-copy { flex: 1; min-width: 0; }
.agent-head-copy h2 { margin: 0; font-size: 15px; font-weight: 800; letter-spacing: -0.2px; }
.agent-head-copy p {
  margin: 1px 0 0;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.82);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.agent-head-clear, .agent-head-close {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.14);
  color: #fff;
  cursor: pointer;
  transition: background 0.15s;
}
.agent-head-clear svg, .agent-head-close svg { width: 17px; height: 17px; }
.agent-head-clear:hover, .agent-head-close:hover { background: rgba(255, 255, 255, 0.26); }


/* ---------- Body / scroll area ---------- */
.agent-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 18px 16px;
  background:
    radial-gradient(circle at 90% 4%, rgba(13, 148, 136, 0.05), transparent 30%),
    #f4f7fb;
  scroll-behavior: smooth;
}

/* Welcome state */
.agent-welcome { text-align: center; padding: 12px 6px; }
.agent-welcome-icon {
  width: 58px;
  height: 58px;
  margin: 0 auto 14px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #0d9488;
  background: linear-gradient(135deg, #f0fdfa, #ccfbf1);
  border: 1px solid #a7f3d0;
}
.agent-welcome-icon svg { width: 30px; height: 30px; }
.agent-welcome h3 { margin: 0 0 6px; font-size: 17px; font-weight: 800; color: #0f172a; }
.agent-welcome p { margin: 0 auto 18px; font-size: 13px; color: #64748b; line-height: 1.55; max-width: 280px; }

.agent-suggestions { display: flex; flex-direction: column; gap: 8px; }
.agent-suggestion {
  padding: 10px 14px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #0f766e;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s, transform 0.1s;
}
.agent-suggestion:hover { border-color: #0d9488; background: #f0fdfa; }
.agent-suggestion:active { transform: scale(0.98); }

/* Message rows */
.agent-msg { display: flex; align-items: flex-end; gap: 8px; margin-bottom: 14px; }
.agent-msg--user { flex-direction: row-reverse; }

.agent-msg-avatar {
  width: 30px;
  height: 30px;
  flex-shrink: 0;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: linear-gradient(135deg, #0d9488, #0e7490);
  box-shadow: 0 3px 8px rgba(13, 148, 136, 0.3);
}
.agent-msg-avatar svg { width: 17px; height: 17px; }

.agent-bubble {
  max-width: 78%;
  padding: 11px 14px;
  border-radius: 16px;
  font-size: 13.5px;
  line-height: 1.55;
  word-wrap: break-word;
  overflow-wrap: anywhere;
}
.agent-msg--bot .agent-bubble {
  background: #ffffff;
  color: #0f172a;
  border: 1px solid #e8eef5;
  border-bottom-left-radius: 5px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
}
.agent-msg--user .agent-bubble {
  background: linear-gradient(120deg, #0d9488, #0e7490);
  color: #ffffff;
  border-bottom-right-radius: 5px;
  box-shadow: 0 4px 12px rgba(13, 148, 136, 0.28);
}

/* Markdown content */
.agent-markdown > *:first-child { margin-top: 0; }
.agent-markdown > *:last-child { margin-bottom: 0; }
.agent-markdown p { margin: 0 0 8px; }
.agent-markdown ul, .agent-markdown ol { margin: 6px 0 8px; padding-left: 20px; }
.agent-markdown li { margin: 3px 0; }
.agent-markdown strong { font-weight: 700; }
.agent-markdown code {
  padding: 1px 6px;
  border-radius: 5px;
  background: #f1f5f9;
  font-size: 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.agent-msg--user .agent-markdown code { background: rgba(255, 255, 255, 0.22); }
.agent-markdown h1, .agent-markdown h2, .agent-markdown h3 { margin: 10px 0 6px; font-size: 15px; font-weight: 800; }
.agent-markdown a { color: #0d9488; text-decoration: underline; }
.agent-msg--user .agent-markdown a { color: #ccfbf1; }

/* Typing indicator */
.agent-typing { display: inline-flex; gap: 4px; align-items: center; padding: 2px 0; }
.agent-typing span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #94a3b8;
  animation: agent-bounce 1.3s infinite ease-in-out;
}
.agent-typing span:nth-child(2) { animation-delay: 0.15s; }
.agent-typing span:nth-child(3) { animation-delay: 0.3s; }
@keyframes agent-bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.5; }
  30% { transform: translateY(-5px); opacity: 1; }
}

/* ---------- Input ---------- */
.agent-input {
  flex-shrink: 0;
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 12px 14px;
  border-top: 1px solid #e8eef5;
  background: #fff;
}
.agent-textarea {
  flex: 1;
  min-height: 42px;
  max-height: 120px;
  padding: 11px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: #f8fafc;
  font-family: inherit;
  font-size: 13.5px;
  line-height: 1.4;
  color: #0f172a;
  resize: none;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.agent-textarea:focus {
  border-color: #0d9488;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.12);
}
.agent-textarea::placeholder { color: #94a3b8; }

.agent-send {
  width: 42px;
  height: 42px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 13px;
  background: linear-gradient(135deg, #0d9488, #0e7490);
  color: #fff;
  cursor: pointer;
  box-shadow: 0 6px 16px rgba(13, 148, 136, 0.32);
  transition: transform 0.1s, box-shadow 0.15s, opacity 0.15s;
}
.agent-send svg { width: 19px; height: 19px; }
.agent-send:hover:not(:disabled) { box-shadow: 0 8px 20px rgba(13, 148, 136, 0.42); }
.agent-send:active:not(:disabled) { transform: scale(0.94); }
.agent-send:disabled { opacity: 0.45; cursor: not-allowed; box-shadow: none; }

/* ---------- Responsive ---------- */
@media (max-width: 480px) {
  .agent-fab { right: 16px; bottom: 16px; height: 50px; padding: 0 16px 0 14px; }
  .agent-fab-label { display: none; }
  .agent-fab--active { padding: 0 14px; }
  .agent-panel {
    right: 0;
    left: 0;
    bottom: 0;
    width: 100%;
    max-width: 100%;
    height: 82vh;
    max-height: 82vh;
    border-radius: 20px 20px 0 0;
    border: none;
    border-top: 1px solid #e8eef5;
  }
}
</style>

