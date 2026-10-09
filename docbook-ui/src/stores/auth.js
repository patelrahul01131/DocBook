import { defineStore } from 'pinia'
import { ref } from 'vue'

const API = '/api/method'


export async function loginUser(email, password) {
  const response = await fetch(`${API}/login`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded"
    },
    body: new URLSearchParams({
      usr: email,
      pwd: password
    })
  });

  const result = await response.json();

  if (!response.ok || result.exc) {
    throw new Error(
      result._server_messages
        ? JSON.parse(result._server_messages)
            .map(item => JSON.parse(item).message)
            .join(", ")
        : "Login failed. Check your email and password."
    );
  }

  // Identify the account and get its dashboard route.
  const profileResponse = await fetch(
    `${API}/docbook.api.auth.get_current_user`,
    {
      credentials: "include"
    }
  );

  const profileResult = await profileResponse.json();

  if (!profileResponse.ok || profileResult.exc) {
    throw new Error("Unable to identify your DocBook profile.");
  }

  return profileResult.message;
}

export async function signupPatient(form) {
  const response = await fetch(
    `${API}/docbook.api.auth.signup`,
    {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        full_name: form.full_name,
        email: form.email,
        password: form.password,
        phone: form.phone
      })
    }
  );

  const result = await response.json();

  if (!response.ok || result.exc) {
    throw new Error("Signup failed. Please check your details.");
  }

  return result.message;
}



export const useAuthStore = defineStore('auth', () => {
  const user = ref({
		email:'patient1@gmail.com',
		full_name:'Rahul Patel'
	})
  const isLoggedIn = ref(false)

  function setUser(userData) {
    user.value = userData
    isLoggedIn.value = true
  }

  function logout() {
    user.value = null
    isLoggedIn.value = false
  }

  return {
    user,
    isLoggedIn,
    setUser,
    logout
  }
})