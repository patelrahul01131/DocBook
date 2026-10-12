
<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { signupPatient } from '../stores/auth'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const isSignup = ref(false)
const loading = ref(false)
const error = ref('')
const success = ref('')

const form = ref({
  full_name: '',
  email: '',
  password: '',
  phone: ''
})

async function submitForm() {
  loading.value = true
  error.value = ''
  success.value = ''

  try {
    if (isSignup.value) {
      await signupPatient(form.value)

      success.value = 'Account created! Please log in.'
      isSignup.value = false
      form.value.password = ''
    } else {
      // Authenticate and update the Pinia store.
      const profile = await auth.login(
        form.value.email,
        form.value.password
      )

      // If the user was redirected to login from a specific page, go back.
      const redirect = route.query.redirect
      if (redirect) {
        await router.push(redirect)
        return
      }

      // Redirect using the role returned by the backend.
      if (profile.role === 'Doctor') {
        await router.push('/doctor')
      } else if (profile.role === 'Patient') {
        await router.push('/home')
      } else {
        await router.push('/')
      }
    }
  } catch (err) {
    error.value =
      err.message || 'Something went wrong. Please try again.'
  } finally {
    loading.value = false
  }
}

function toggleMode() {
  isSignup.value = !isSignup.value
  error.value = ''
  success.value = ''
  form.value.password = ''
}
</script>

<template>
  <main class="auth-page">
    <a href="/" class="auth-home-link">
      <span>←</span> Back to home
    </a>

    <section class="auth-card">
      <div class="auth-logo">
        <div class="auth-logo-mark">🩺</div>
        <span class="auth-logo-name">DocBook</span>
      </div>

      <h1>{{ isSignup ? 'Create Patient Account' : 'Welcome Back' }}</h1>

      <p>
        {{
          isSignup
            ? 'Register to book doctor appointments.'
            : 'Log in to continue to DocBook.'
        }}
      </p>

      <form @submit.prevent="submitForm">
        <label v-if="isSignup">
          Full Name
          <input
            v-model="form.full_name"
            type="text"
            required
            autocomplete="name"
          />
        </label>

        <label>
          Email
          <input
            v-model="form.email"
            type="email"
            required
            autocomplete="email"
          />
        </label>

        <label v-if="isSignup">
          Phone
          <input
            v-model="form.phone"
            type="tel"
            autocomplete="tel"
          />
        </label>

        <label>
          Password
          <input
            v-model="form.password"
            type="password"
            required
            :minlength="isSignup ? 8 : undefined"
            :autocomplete="isSignup ? 'new-password' : 'current-password'"
          />
        </label>

        <p v-if="error" class="error">{{ error }}</p>
        <p v-if="success" class="success">{{ success }}</p>

        <button type="submit" :disabled="loading">
          {{
            loading
              ? 'Please wait...'
              : isSignup
                ? 'Create Account'
                : 'Log In'
          }}
        </button>
      </form>

      <p class="switch-mode">
        {{ isSignup ? 'Already have an account?' : 'New to DocBook?' }}

        <button
          type="button"
          class="text-button"
          @click="toggleMode"
        >
          {{ isSignup ? 'Log In' : 'Sign Up as Patient' }}
        </button>
      </p>

      <p class="doctor-note">
        Doctors: use your hospital-provided account to log in.
      </p>
    </section>
  </main>
</template>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 24px;
  background:
    radial-gradient(circle at 15% 12%, rgba(13, 148, 136, 0.12), transparent 38%),
    radial-gradient(circle at 85% 18%, rgba(37, 99, 235, 0.10), transparent 40%),
    #f4f7fb;
}

.auth-home-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  text-decoration: none;
  padding: 8px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid #e2e8f0;
  transition: color 0.15s, border-color 0.15s;
}
.auth-home-link:hover { color: #0d9488; border-color: #0d9488; }

.auth-card {
  width: 100%;
  max-width: 420px;
  padding: 32px;
  border-radius: 20px;
  background: white;
  box-shadow: 0 12px 40px #16233a12;
}

.auth-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
}

.auth-logo-mark {
  width: 38px;
  height: 38px;
  border-radius: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 19px;
  background: linear-gradient(135deg, #0d9488, #0e7490);
  box-shadow: 0 6px 16px rgba(13, 148, 136, 0.28);
}

.auth-logo-name {
  font-size: 18px;
  font-weight: 800;
  letter-spacing: -0.4px;
  color: #0f172a;
}

h1 {
  margin: 0 0 8px;
}

.auth-card > p {
  color: #64748b;
}

form,
label {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

form {
  gap: 18px;
  margin-top: 24px;
}

input {
  width: 100%;
  box-sizing: border-box;
  padding: 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
}

button {
  padding: 12px;
  border: 0;
  border-radius: 8px;
  cursor: pointer;
  background: #0f766e;
  color: white;
}

button:disabled {
  opacity: 0.6;
  cursor: wait;
}

.text-button {
  padding: 0;
  background: transparent;
  color: #0f766e;
}

.switch-mode {
  margin-top: 20px;
  text-align: center;
}

.doctor-note {
  font-size: 13px;
  text-align: center;
}

.error {
  color: #dc2626;
}

.success {
  color: #15803d;
}
</style>