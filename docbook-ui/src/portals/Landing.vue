<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Button } from 'frappe-ui'

const router = useRouter()

const mobileOpen = ref(false)

// Highlight stats shown on the landing page.
const highlights = [
  { value: '24/7', label: 'Book anytime' },
  { value: '50+', label: 'Specialist doctors' },
  { value: '15 min', label: 'Reminder checks' },
]

const features = [
  {
    icon: 'lucide-search',
    title: 'Find the right doctor',
    text: 'Browse verified specialists by specialty, experience, and fee.',
    accent: 'blue',
  },
  {
    icon: 'lucide-calendar-check',
    title: 'Book in seconds',
    text: 'Real-time slots that respect doctor schedules and holidays.',
    accent: 'teal',
  },
  {
    icon: 'lucide-pill',
    title: 'Smart prescriptions',
    text: 'Medicines, dosages and treatment plans in one secure place.',
    accent: 'amber',
  },
  {
    icon: 'lucide-bell',
    title: 'Medicine reminders',
    text: 'Automated email reminders so you never miss a dose.',
    accent: 'purple',
  },
]

const steps = [
  { n: '1', title: 'Create your account', text: 'Sign up as a patient in under a minute.' },
  { n: '2', title: 'Pick your doctor', text: 'Compare specialists and choose the best fit.' },
  { n: '3', title: 'Book & get care', text: 'Reserve a slot and manage everything online.' },
]

function goLogin() {
  router.push('/login')
}

function goSignup() {
  router.push('/signup')
}
</script>

<template>
  <div class="lp">
    <!-- ============ Navbar ============ -->
    <header class="lp-nav">
      <div class="lp-nav-inner">
        <div class="lp-brand">
          <div class="lp-brand-mark">🩺</div>
          <div class="lp-brand-copy">
            <span class="lp-brand-name">DocBook</span>
            <span class="lp-brand-tag">Health, simplified</span>
          </div>
        </div>

        <nav class="lp-nav-links" :class="{ 'is-open': mobileOpen }">
          <a href="#features" @click.prevent="mobileOpen = false">Features</a>
          <a href="#how" @click.prevent="mobileOpen = false">How it works</a>
          <a href="#start" @click.prevent="mobileOpen = false">Get started</a>
        </nav>

        <div class="lp-nav-actions">
          <Button label="Log in" @click="goLogin" />
          <Button label="Sign up free" variant="solid" theme="green" @click="goSignup" class="lp-btn-teal" />
          <button
            class="lp-burger"
            type="button"
            :aria-expanded="mobileOpen"
            aria-label="Toggle menu"
            @click="mobileOpen = !mobileOpen"
          >
            <span></span><span></span><span></span>
          </button>
        </div>
      </div>
    </header>

    <!-- ============ Hero ============ -->
    <section class="lp-hero" id="start">
      <div class="lp-hero-glow" aria-hidden="true"></div>
      <div class="lp-hero-inner">
        <div class="lp-hero-copy">
          <div class="lp-pill">
            <span class="lp-pill-dot"></span>
            Trusted healthcare appointments
          </div>
          <h1>Book doctor appointments, <span class="lp-grad">effortlessly</span>.</h1>
          <p class="lp-lede">
            DocBook connects patients with verified doctors. Manage appointments,
            prescriptions and medicine reminders — all from one beautiful dashboard.
          </p>

          <div class="lp-hero-cta">
            <Button label="Book as Patient" variant="solid" theme="green" size="lg" @click="goSignup" class="lp-btn-teal" />
            <Button label="Doctor Login" size="lg" @click="goLogin" />
          </div>

          <div class="lp-highlights">
            <div v-for="h in highlights" :key="h.label" class="lp-highlight">
              <strong>{{ h.value }}</strong>
              <span>{{ h.label }}</span>
            </div>
          </div>
        </div>

        <div class="lp-hero-art" aria-hidden="true">
          <div class="lp-card-float lp-card-float--1">
            <div class="lp-fc-icon blue"><span class="lucide-calendar-check"></span></div>
            <div>
              <strong>Appointment confirmed</strong>
              <span>Dr. Sharma · Tomorrow 10:00</span>
            </div>
          </div>
          <div class="lp-card-float lp-card-float--2">
            <div class="lp-fc-icon teal"><span class="lucide-stethoscope"></span></div>
            <div>
              <strong>Find specialists</strong>
              <span>Cardiology, Dental, &amp; more</span>
            </div>
          </div>
          <div class="lp-card-float lp-card-float--3">
            <div class="lp-fc-icon amber"><span class="lucide-bell"></span></div>
            <div>
              <strong>Medicine reminder</strong>
              <span>Take vitamin D · 9:00 PM</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ============ Features ============ -->
    <section class="lp-section" id="features">
      <div class="lp-section-head">
        <div class="lp-eyebrow">WHY DOCBOOK</div>
        <h2>Everything you need for modern care</h2>
        <p>A complete patient &amp; doctor experience, built for speed and clarity.</p>
      </div>

      <div class="lp-feature-grid">
        <article v-for="f in features" :key="f.title" class="lp-feature">
          <div class="lp-feature-icon" :class="`accent-${f.accent}`">
            <span :class="f.icon"></span>
          </div>
          <h3>{{ f.title }}</h3>
          <p>{{ f.text }}</p>
        </article>
      </div>
    </section>

    <!-- ============ How it works ============ -->
    <section class="lp-section lp-section--tint" id="how">
      <div class="lp-section-head">
        <div class="lp-eyebrow">HOW IT WORKS</div>
        <h2>Get care in three simple steps</h2>
        <p>From sign-up to consultation, DocBook keeps it simple.</p>
      </div>

      <div class="lp-steps">
        <article v-for="s in steps" :key="s.n" class="lp-step">
          <div class="lp-step-n">{{ s.n }}</div>
          <h3>{{ s.title }}</h3>
          <p>{{ s.text }}</p>
        </article>
      </div>
    </section>

    <!-- ============ CTA ============ -->
    <section class="lp-cta-band">
      <div class="lp-cta-card">
        <h2>Ready to take control of your health?</h2>
        <p>Create a free patient account, or log in to your doctor portal.</p>
        <div class="lp-cta-actions">
          <Button label="Create free account" variant="solid" theme="green" size="lg" @click="goSignup" class="lp-btn-teal" />
          <Button label="I already have an account" size="lg" @click="goLogin" class="lp-btn-light" />
        </div>
      </div>
    </section>

    <!-- ============ Footer ============ -->
    <footer class="lp-footer">
      <div class="lp-footer-brand">
        <div class="lp-brand-mark">🩺</div>
        <span>DocBook</span>
      </div>
      <p>© {{ new Date().getFullYear() }} DocBook. Book appointments, the smart way.</p>
      <div class="lp-footer-links">
        <a href="#features" @click.prevent>Features</a>
        <a href="#how" @click.prevent>How it works</a>
        <button type="button" @click="goLogin">Log in</button>
      </div>
    </footer>
  </div>
</template>


<style scoped>
.lp {
  min-height: 100vh;
  background: #f4f7fb;
  color: #0f172a;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.lp-grad {
  background: linear-gradient(120deg, #0d9488, #2563eb);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

/* ---------- Navbar ---------- */
.lp-nav {
  position: sticky;
  top: 0;
  z-index: 50;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(14px);
  border-bottom: 1px solid #e8eef5;
}

.lp-nav-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 14px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.lp-brand { display: flex; align-items: center; gap: 11px; }

.lp-brand-mark {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  background: linear-gradient(135deg, #0d9488, #0e7490);
  box-shadow: 0 6px 16px rgba(13, 148, 136, 0.28);
}

.lp-brand-copy { display: flex; flex-direction: column; line-height: 1.1; }
.lp-brand-name { font-size: 18px; font-weight: 800; letter-spacing: -0.4px; }
.lp-brand-tag { font-size: 11px; color: #0d9488; font-weight: 600; }

.lp-nav-links { display: flex; gap: 28px; }
.lp-nav-links a {
  font-size: 14px;
  font-weight: 600;
  color: #475569;
  text-decoration: none;
  transition: color 0.15s;
}
.lp-nav-links a:hover { color: #0d9488; }

.lp-nav-actions { display: flex; align-items: center; gap: 10px; }

.lp-burger {
  display: none;
  flex-direction: column;
  gap: 5px;
  padding: 8px;
  background: none;
  border: none;
  cursor: pointer;
}
.lp-burger span {
  width: 22px;
  height: 2px;
  border-radius: 2px;
  background: #0f172a;
}

/* ---------- Hero ---------- */
.lp-hero {
  position: relative;
  overflow: hidden;
  padding: 72px 24px 88px;
}

.lp-hero-glow {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 18% 12%, rgba(13, 148, 136, 0.14), transparent 38%),
    radial-gradient(circle at 82% 22%, rgba(37, 99, 235, 0.12), transparent 40%);
  pointer-events: none;
}

.lp-hero-inner {
  position: relative;
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  gap: 48px;
  align-items: center;
}

.lp-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 999px;
  background: #fff;
  border: 1px solid #e2e8f0;
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
}

.lp-pill-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2);
}

.lp-hero-copy h1 {
  margin: 20px 0 16px;
  font-size: 52px;
  font-weight: 800;
  line-height: 1.05;
  letter-spacing: -1.5px;
}

.lp-lede {
  margin: 0 0 30px;
  font-size: 17px;
  line-height: 1.6;
  color: #475569;
  max-width: 520px;
}

.lp-hero-cta { display: flex; gap: 12px; flex-wrap: wrap; }

/* Brand teal overrides for frappe-ui Buttons (valid theme=green base) */
:deep(.lp-btn-teal) {
  background: linear-gradient(120deg, #0d9488, #0e7490) !important;
  border-color: transparent !important;
  color: #fff !important;
  box-shadow: 0 8px 20px rgba(13, 148, 136, 0.3);
}
:deep(.lp-btn-teal:hover) {
  background: linear-gradient(120deg, #0f766e, #155e75) !important;
}

:deep(.lp-btn-light) {
  background: rgba(255, 255, 255, 0.16) !important;
  border-color: rgba(255, 255, 255, 0.4) !important;
  color: #fff !important;
}
:deep(.lp-btn-light:hover) {
  background: rgba(255, 255, 255, 0.26) !important;
}

.lp-highlights {
  display: flex;
  gap: 36px;
  margin-top: 40px;
  flex-wrap: wrap;
}

.lp-highlight { display: flex; flex-direction: column; }
.lp-highlight strong { font-size: 26px; font-weight: 800; letter-spacing: -0.5px; }
.lp-highlight span { font-size: 13px; color: #64748b; }


/* ---------- Hero art (floating cards) ---------- */
.lp-hero-art {
  position: relative;
  height: 420px;
}

.lp-card-float {
  position: absolute;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 18px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid #eef2f7;
  box-shadow: 0 18px 44px rgba(15, 23, 42, 0.12);
  animation: lp-float 6s ease-in-out infinite;
}
.lp-card-float strong { display: block; font-size: 14px; color: #0f172a; }
.lp-card-float span { font-size: 12px; color: #64748b; }

.lp-card-float--1 { top: 20px; left: 6%; animation-delay: 0s; }
.lp-card-float--2 { top: 150px; right: 2%; animation-delay: 1.2s; }
.lp-card-float--3 { bottom: 20px; left: 16%; animation-delay: 2.4s; }

.lp-fc-icon {
  width: 46px;
  height: 46px;
  border-radius: 14px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}
.lp-fc-icon.blue { background: #eff6ff; color: #2563eb; }
.lp-fc-icon.teal { background: #f0fdfa; color: #0d9488; }
.lp-fc-icon.amber { background: #fffbeb; color: #d97706; }

@keyframes lp-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-12px); }
}

/* ---------- Sections ---------- */
.lp-section { padding: 76px 24px; }
.lp-section--tint { background: #fff; }

.lp-section-head {
  max-width: 640px;
  margin: 0 auto 44px;
  text-align: center;
}

.lp-eyebrow {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 1.4px;
  color: #0d9488;
  margin-bottom: 10px;
}

.lp-section-head h2 {
  margin: 0 0 12px;
  font-size: 34px;
  font-weight: 800;
  letter-spacing: -0.8px;
}
.lp-section-head p { margin: 0; font-size: 16px; color: #64748b; }

/* ---------- Features ---------- */
.lp-feature-grid {
  max-width: 1100px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.lp-feature {
  padding: 26px 22px;
  border-radius: 20px;
  background: #fff;
  border: 1px solid #eef2f7;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
  transition: transform 0.15s, box-shadow 0.15s;
}
.lp-feature:hover { transform: translateY(-4px); box-shadow: 0 16px 36px rgba(15, 23, 42, 0.1); }

.lp-feature-icon {
  width: 50px;
  height: 50px;
  border-radius: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  margin-bottom: 16px;
}
.lp-feature-icon.accent-blue { background: #eff6ff; color: #2563eb; }
.lp-feature-icon.accent-teal { background: #f0fdfa; color: #0d9488; }
.lp-feature-icon.accent-amber { background: #fffbeb; color: #d97706; }
.lp-feature-icon.accent-purple { background: #f5f3ff; color: #7c3aed; }

.lp-feature h3 { margin: 0 0 8px; font-size: 17px; font-weight: 700; }
.lp-feature p { margin: 0; font-size: 14px; color: #64748b; line-height: 1.55; }

/* ---------- Steps ---------- */
.lp-steps {
  max-width: 1000px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}

.lp-step {
  padding: 28px 24px;
  border-radius: 20px;
  background: #f8fafc;
  border: 1px solid #eef2f7;
  text-align: center;
}
.lp-step-n {
  width: 52px;
  height: 52px;
  border-radius: 16px;
  margin: 0 auto 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 800;
  color: #fff;
  background: linear-gradient(135deg, #0d9488, #0e7490);
}
.lp-step h3 { margin: 0 0 8px; font-size: 18px; font-weight: 700; }
.lp-step p { margin: 0; font-size: 14px; color: #64748b; }


/* ---------- CTA band ---------- */
.lp-cta-band { padding: 20px 24px 76px; }

.lp-cta-card {
  max-width: 900px;
  margin: 0 auto;
  padding: 52px 40px;
  border-radius: 28px;
  text-align: center;
  color: #fff;
  background: linear-gradient(120deg, #0f766e 0%, #0d9488 50%, #2563eb 130%);
  box-shadow: 0 24px 56px rgba(13, 118, 110, 0.32);
}

.lp-cta-card h2 { margin: 0 0 12px; font-size: 32px; font-weight: 800; letter-spacing: -0.6px; }
.lp-cta-card p { margin: 0 0 28px; font-size: 16px; color: rgba(255, 255, 255, 0.9); }

.lp-cta-actions { display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }

/* ---------- Footer ---------- */
.lp-footer {
  padding: 32px 24px;
  border-top: 1px solid #e8eef5;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.lp-footer-brand { display: flex; align-items: center; gap: 10px; font-weight: 800; }
.lp-footer-brand .lp-brand-mark { width: 32px; height: 32px; font-size: 16px; border-radius: 9px; }
.lp-footer p { margin: 0; font-size: 13px; color: #94a3b8; }

.lp-footer-links { display: flex; gap: 20px; align-items: center; }
.lp-footer-links a, .lp-footer-links button {
  font-size: 13px;
  color: #64748b;
  text-decoration: none;
  background: none;
  border: none;
  cursor: pointer;
  font-weight: 600;
}
.lp-footer-links a:hover, .lp-footer-links button:hover { color: #0d9488; }

/* ---------- Responsive ---------- */
@media (max-width: 900px) {
  .lp-hero-inner { grid-template-columns: 1fr; }
  .lp-hero-art { display: none; }
  .lp-hero-copy h1 { font-size: 40px; }
  .lp-feature-grid { grid-template-columns: repeat(2, 1fr); }
  .lp-steps { grid-template-columns: 1fr; }
}

@media (max-width: 640px) {
  .lp-nav-links {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    flex-direction: column;
    gap: 0;
    padding: 8px 24px 16px;
    background: #fff;
    border-bottom: 1px solid #e8eef5;
    box-shadow: 0 12px 24px rgba(15, 23, 42, 0.06);
    display: none;
  }
  .lp-nav-links.is-open { display: flex; }
  .lp-nav-links a { padding: 12px 0; }
  .lp-burger { display: flex; }
  .lp-cta { display: none; }
  .lp-hero { padding: 48px 20px 64px; }
  .lp-hero-copy h1 { font-size: 34px; }
  .lp-section { padding: 56px 20px; }
  .lp-section-head h2 { font-size: 26px; }
  .lp-feature-grid { grid-template-columns: 1fr; }
  .lp-cta-card { padding: 40px 24px; }
  .lp-cta-card h2 { font-size: 26px; }
  .lp-footer { justify-content: center; text-align: center; }
}
</style>

