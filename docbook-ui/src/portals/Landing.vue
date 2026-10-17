<script setup>
import { useRouter } from 'vue-router'
import { Button } from 'frappe-ui'

const router = useRouter()

function goHome() { router.push('/home') }
function goLogin() { router.push('/login') }
function goSignup() { router.push('/signup') }
</script>

<template>
  <div class="landing">
    <nav class="land-nav">
      <div class="land-nav-inner">
        <div class="land-brand">
          <div class="land-mark">🩺</div>
          <div class="land-name">DocBook</div>
        </div>
        <div class="land-links">
          <a href="#features" class="land-link">Features</a>
          <a href="#how-it-works" class="land-link">How it works</a>
          <a href="#specialties" class="land-link">Specialties</a>
        </div>
        <div class="land-actions">
          <Button label="Log in" @click="goLogin" />
          <Button label="Sign up" variant="solid" theme="green" class="land-btn-primary" @click="goSignup" />
        </div>
      </div>
    </nav>

    <header class="land-hero">
      <div class="land-hero-inner">
        <div class="land-hero-content">
          <span class="land-hero-kicker">Healthcare made simple</span>
          <h1 class="land-hero-title">Book the right doctor<br /><span class="land-title-highlight">in seconds.</span></h1>
          <p class="land-hero-desc">Describe your symptoms and our AI triage matches you with the right specialist, then book your appointment instantly — no phone calls, no waiting rooms.</p>
          <div class="land-hero-actions">
            <Button label="Start AI Booking" variant="solid" theme="green" size="lg" class="land-btn-hero" @click="goHome" />
            <Button label="Browse Doctors" size="lg" class="land-btn-secondary" @click="goHome" />
          </div>
          <div class="land-hero-trust"><span class="land-trust-dot"></span><span>Trusted by 10,000+ patients</span></div>
        </div>
        <div class="land-hero-visual">
          <div class="land-visual-card">
            <div class="land-visual-icon">🏥</div>
            <div class="land-visual-box"><div class="land-stat big">10k+</div><div class="land-stat-label">patients</div></div>
            <div class="land-visual-box land-visual-box--small"><div class="land-stat">500+</div><div class="land-stat-label">doctors</div></div>
          </div>
        </div>
      </div>
    </header>
    <section id="features" class="land-section land-features">
      <div class="land-section-inner">
        <div class="land-section-head"><h2 class="land-section-title">Why choose DocBook?</h2><p class="land-section-sub">Everything you need to manage your care in one place.</p></div>
        <div class="land-feature-grid">
          <div class="land-feature-card"><div class="land-feature-icon">🩺</div><h3 class="land-feature-title">AI-Powered Triage</h3><p class="land-feature-desc">Describe your symptoms and let AI match you with the right specialist.</p></div>
          <div class="land-feature-card"><div class="land-feature-icon">📅</div><h3 class="land-feature-title">Smart Booking</h3><p class="land-feature-desc">Book appointments with verified doctors and get instant confirmation.</p></div>
          <div class="land-feature-card"><div class="land-feature-icon">📄</div><h3 class="land-feature-title">Medical Reports</h3><p class="land-feature-desc">Upload and preview lab results, imaging, and prescriptions securely.</p></div>
          <div class="land-feature-card"><div class="land-feature-icon">⚡</div><h3 class="land-feature-title">Fast Track</h3><p class="land-feature-desc">Priority slots for urgent cases based on AI-assessed urgency.</p></div>
        </div>
      </div>
    </section>

    <section id="how-it-works" class="land-section land-steps">
      <div class="land-section-inner">
        <div class="land-section-head"><h2 class="land-section-title">How it works</h2><p class="land-section-sub">From symptoms to appointment in three steps.</p></div>
        <div class="land-step-grid">
          <div class="land-step-card"><div class="land-step-num">1</div><h3 class="land-step-title">Describe your problem</h3><p class="land-step-desc">Tell our AI your symptoms in plain words.</p></div>
          <div class="land-step-card"><div class="land-step-num">2</div><h3 class="land-step-title">AI finds the specialist</h3><p class="land-step-desc">AI identifies the right specialty and matches available doctors.</p></div>
          <div class="land-step-card"><div class="land-step-num">3</div><h3 class="land-step-title">Book your appointment</h3><p class="land-step-desc">Pick a slot and confirm — you\'re all set.</p></div>
        </div>
      </div>
    </section>

    <section id="specialties" class="land-section land-specialties">
      <div class="land-section-inner">
        <div class="land-section-head"><h2 class="land-section-title">Specialties</h2><p class="land-section-sub">We cover all major medical specialties.</p></div>
        <div class="land-specialty-grid">
          <div class="land-specialty-chip">Cardiology</div>
          <div class="land-specialty-chip">Dermatology</div>
          <div class="land-specialty-chip">Pediatrics</div>
          <div class="land-specialty-chip">Gynecology</div>
          <div class="land-specialty-chip">Orthopedics</div>
          <div class="land-specialty-chip">Neurology</div>
          <div class="land-specialty-chip">General Medicine</div>
        </div>
      </div>
    </section>

    <footer class="land-footer">
      <div class="land-footer-inner">
        <div class="land-footer-brand"><div class="land-mark">🩺</div><div class="land-name" style="font-size: 18px; font-weight: 800;">DocBook</div></div>
        <p class="land-footer-copy">© 2026 DocBook. AI-powered patient care.</p>
        <div class="land-footer-actions">
          <Button label="Log in" @click="goLogin" />
          <Button label="Sign up" variant="solid" theme="green" class="land-btn-primary" @click="goSignup" />
        </div>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.landing { min-height: 100vh; background: #f4f7fb; color: #0f172a; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
.land-nav { position: sticky; top: 0; z-index: 50; background: rgba(255,255,255,0.85); backdrop-filter: blur(12px); border-bottom: 1px solid #e2e8f0; }
.land-nav-inner { max-width: 1100px; margin: 0 auto; padding: 14px 24px; display: flex; align-items: center; justify-content: space-between; gap: 20px; }
.land-brand { display: flex; align-items: center; gap: 10px; }
.land-mark { width: 34px; height: 34px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 18px; background: linear-gradient(135deg, #0d9488, #0e7490); }
.land-name { font-size: 18px; font-weight: 900; letter-spacing: -0.5px; }
.land-links { display: flex; align-items: center; gap: 24px; }
.land-link { color: #475569; text-decoration: none; font-size: 14px; font-weight: 600; }
.land-link:hover { color: #0d9488; }
.land-actions { display: flex; align-items: center; gap: 10px; }
.land-btn-primary { background: #0d9488 !important; color: #fff !important; }
.land-btn-secondary { background: #fff !important; border: 1px solid #e2e8f0 !important; color: #0f172a !important; }
.land-hero { padding: 80px 24px 60px; position: relative; overflow: hidden; }
.land-hero::before { content: ''; position: absolute; top: -10%; right: -10%; width: 600px; height: 600px; border-radius: 50%; background: #e0f2fe; filter: blur(100px); z-index: -1; }
.land-hero-inner { max-width: 1100px; margin: 0 auto; display: grid; grid-template-columns: 1fr 460px; gap: 50px; align-items: center; }
.land-hero-kicker { display: inline-block; font-size: 12px; font-weight: 800; letter-spacing: 1.5px; text-transform: uppercase; color: #0d9488; margin-bottom: 12px; }
.land-hero-title { font-size: clamp(40px, 7vw, 64px); font-weight: 900; line-height: 1.1; letter-spacing: -1px; margin: 0 0 18px; }
.land-title-highlight { color: #0d9488; }
.land-hero-desc { font-size: 18px; color: #475569; margin: 0 0 28px; line-height: 1.7; max-width: 520px; }
.land-hero-actions { display: flex; gap: 14px; align-items: center; flex-wrap: wrap; margin-bottom: 24px; }
.land-btn-hero { padding: 14px 28px !important; font-size: 16px !important; font-weight: 800 !important; }
.land-hero-trust { display: flex; align-items: center; gap: 10px; font-size: 13px; color: #64748b; font-weight: 600; }
.land-trust-dot { width: 8px; height: 8px; border-radius: 50%; background: #0d9488; display: inline-block; }
.land-visual-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 24px; padding: 32px; box-shadow: 0 20px 50px rgba(15, 23, 42, 0.1); display: flex; flex-direction: column; gap: 20px; }
.land-visual-icon { font-size: 48px; margin-bottom: 8px; }
.land-visual-box { display: flex; align-items: center; gap: 14px; padding: 16px; background: #f0fdfa; border-radius: 14px; border: 1px dashed #99f6e4; }
.land-visual-box--small { margin-left: auto; width: 45%; }
.land-stat { font-size: 22px; font-weight: 900; color: #0d9488; }
.land-stat.big { font-size: 32px; }
.land-stat-label { font-size: 13px; color: #64748b; }
.land-section { padding: 70px 24px; }
.land-section-inner { max-width: 1100px; margin: 0 auto; }
.land-section-head { text-align: center; margin-bottom: 40px; }
.land-section-title { font-size: 28px; font-weight: 900; margin: 0 0 12px; letter-spacing: -0.5px; }
.land-section-sub { font-size: 16px; color: #64748b; margin: 0; }
.land-feature-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; }
.land-feature-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 20px; padding: 28px; transition: transform 0.2s, border-color 0.2s; }
.land-feature-card:hover { border-color: #0d9488; transform: translateY(-4px); }
.land-feature-icon { font-size: 32px; margin-bottom: 14px; display: block; }
.land-feature-title { font-size: 17px; font-weight: 800; margin: 0 0 10px; }
.land-feature-desc { font-size: 14px; color: #64748b; margin: 0; line-height: 1.6; }
.land-step-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 20px; }
.land-step-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 20px; padding: 32px 24px; display: flex; flex-direction: column; gap: 14px; }
.land-step-num { width: 40px; height: 40px; border-radius: 50%; background: #0d9488; color: #fff; display: flex; align-items: center; justify-content: center; font-size: 18px; font-weight: 900; }
.land-step-title { font-size: 16px; font-weight: 800; margin: 0; }
.land-step-desc { font-size: 14px; color: #64748b; margin: 0; line-height: 1.6; }
.land-specialty-grid { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; }
.land-specialty-chip { padding: 10px 20px; border: 1px solid #e2e8f0; border-radius: 999px; background: #fff; color: #475569; font-size: 14px; font-weight: 600; }
.land-specialty-chip:hover { border-color: #0d9488; color: #0d9488; background: #f0fdfa; }
.land-footer { border-top: 1px solid #e2e8f0; margin-top: 60px; padding: 40px 24px; background: #fff; }
.land-footer-inner { max-width: 1100px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; gap: 24px; flex-wrap: wrap; }
.land-footer-brand { display: flex; align-items: center; gap: 10px; }
.land-footer-copy { font-size: 13px; color: #64748b; margin: 0; }
@media (max-width: 900px) { .land-hero-inner { grid-template-columns: 1fr; gap: 40px; } .land-visual-card { display: none; } }
@media (max-width: 600px) { .land-hero { padding: 50px 16px 30px; } .land-section { padding: 40px 16px; } .land-footer-inner { flex-direction: column; text-align: center; align-items: center; gap: 16px; } }
</style>