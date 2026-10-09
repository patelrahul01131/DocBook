import { toast } from 'frappe-ui'

const baseURL = '/api/method'



export async function call(method, params = {}) {
  try {
    const response = await fetch(`${baseURL}/${method}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify(params),
    })

    const data = await response.json()

    if (!response.ok) {
      throw new Error(
        data.message || `Request failed with status ${response.status}`
      )
    }

    return data.message
  } catch (error) {
    toast.error('API Error', {
      description: error.message || 'An error occurred',
    })

    throw error
  }
}