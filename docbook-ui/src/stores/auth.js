
import { defineStore } from 'pinia'
import { ref } from 'vue'

const API = '/api/method'

async function readResponse(response) {
  const result = await response.json().catch(() => ({}))

  if (!response.ok || result.exc) {
    let message = result.message || 'Request failed.'

    // Frappe sometimes returns its error messages as JSON strings.
    if (result._server_messages) {
      try {
        const messages = JSON.parse(result._server_messages)
        message = messages
          .map((item) => {
            try {
              return JSON.parse(item).message
            } catch {
              return item
            }
          })
          .filter(Boolean)
          .join(', ')
      } catch {
        // Keep the fallback message if parsing fails.
      }
    }

    throw new Error(message)
  }

  return result
}

async function getCurrentUserProfile() {
  const response = await fetch(
    `${API}/docbook.api.auth.get_current_user`,
    {
      method: 'GET',
      credentials: 'include',
      headers: {
        Accept: 'application/json'
      }
    }
  )

  const result = await readResponse(response)
  const profile = result.message

  // Never treat Guest or an empty response as a logged-in user.
  if (
    !profile ||
    profile.logged_in === false ||
    profile.is_guest === true ||
    profile.user === 'Guest' ||
    profile.email === 'Guest'
  ) {
    return null
  }

  return profile
}

export async function loginUser(email, password) {
  const response = await fetch(`${API}/login`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      Accept: 'application/json'
    },
    body: new URLSearchParams({
      usr: email.trim(),
      pwd: password
    })
  })

  await readResponse(response)

  // Get the actual profile and role from the backend.
  // Do not infer the role from the email or form.
  try {
    const profile = await getCurrentUserProfile()

    if (!profile) {
      throw new Error('Your DocBook profile could not be identified.')
    }

    return profile
  } catch (error) {
    // Avoid leaving an authenticated Frappe session behind if
    // profile loading fails after a successful login.
    await fetch(`${API}/logout`, {
      method: 'GET',
      credentials: 'include'
    }).catch(() => {})

    throw error
  }
}

export async function signupPatient(form) {
  const response = await fetch(
    `${API}/docbook.api.auth.signup`,
    {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json'
      },
      body: JSON.stringify({
        full_name: form.full_name,
        email: form.email,
        password: form.password,
        phone: form.phone
      })
    }
  )

  const result = await readResponse(response)
  return result.message
}

export const useAuthStore = defineStore('auth', () => {
  // Guest by default: never put a sample user here.
  const user = ref(null)
  const isLoggedIn = ref(false)
  const isLoading = ref(false)

  function setUser(userData) {
    if (!userData) {
      user.value = null
      isLoggedIn.value = false
      return
    }

    user.value = userData
    isLoggedIn.value = true
  }


async function login(email, password) {
  isLoading.value = true

  try {
    const profile = await loginUser(email, password)

    if (!profile || profile.is_guest || !profile.logged_in) {
      throw new Error('Unable to load your DocBook profile.')
    }

    setUser(profile)

    return profile
  } finally {
    isLoading.value = false
  }
}

  async function fetchCurrentUser() {
    isLoading.value = true

    try {
      const profile = await getCurrentUserProfile()
      setUser(profile)
      return profile
    } catch {
      // A missing/expired session should display the guest UI.
      setUser(null)
      return null
    } finally {
      isLoading.value = false
    }
  }

async function logout() {
  isLoading.value = true

  try {
    const response = await fetch('/api/method/logout', {
      method: 'GET',
      credentials: 'include'
    })

    if (!response.ok) {
      throw new Error('Unable to log out from Frappe.')
    }
  } finally {
    setUser(null)
    isLoading.value = false
    // Navigation is handled by the caller (e.g. App.vue) to keep the
    // store free of router coupling and avoid circular imports.
  }
}

  return {
    user,
    isLoggedIn,
    isLoading,
    setUser,
    login,
    fetchCurrentUser,
    logout
  }
})