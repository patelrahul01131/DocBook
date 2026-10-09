
<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { loginUser, signupPatient } from "../stores/auth";

const router = useRouter();

const isSignup = ref(false);
const loading = ref(false);
const error = ref("");
const success = ref("");

const form = ref({
  full_name: "",
  email: "",
  password: "",
  phone: ""
});

async function submitForm() {
  loading.value = true;
  error.value = "";
  success.value = "";

  try {
    if (isSignup.value) {
      await signupPatient(form.value);

      success.value = "Account created! Please log in.";
      isSignup.value = false;
      form.value.password = "";
    } else {
      const profile = await loginUser(
        form.value.email,
        form.value.password
      );

      await router.push(profile.redirect);
    }
  } catch (err) {
    error.value =
      err.message || "Something went wrong. Please try again.";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <main class="auth-page">
    <section class="auth-card">
      <h1>{{ isSignup ? "Create Patient Account" : "Welcome Back" }}</h1>

      <p>
        {{
          isSignup
            ? "Register to book doctor appointments."
            : "Log in to continue to DocBook."
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
              ? "Please wait..."
              : isSignup
                ? "Create Account"
                : "Log In"
          }}
        </button>
      </form>

      <p class="switch-mode">
        {{
          isSignup
            ? "Already have an account?"
            : "New to DocBook?"
        }}

        <button
          type="button"
          class="text-button"
          @click="isSignup = !isSignup; error = ''; success = ''"
        >
          {{ isSignup ? "Log In" : "Sign Up as Patient" }}
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
  display: grid;
  place-items: center;
  padding: 24px;
  background: #f4f7fb;
}

.auth-card {
  width: 100%;
  max-width: 420px;
  padding: 32px;
  border-radius: 18px;
  background: white;
  box-shadow: 0 12px 40px #16233a12;
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