import { toast } from 'frappe-ui'

const baseURL = '/api/method'



export async function call(method, params = {}, options = {}) {
  const quiet = options.quiet === true
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
      let errorMsg = data?.message
      if (data?._server_messages) {
        try {
          const msgs = JSON.parse(data._server_messages)
          if (Array.isArray(msgs) && msgs.length > 0) {
            const first = typeof msgs[0] === 'string' ? JSON.parse(msgs[0]) : msgs[0]
            if (first && first.message) {
              errorMsg = first.message
            }
          }
        } catch (e) {
          // ignore json parse error
        }
      }
      if (!errorMsg && data?.exception) {
        const parts = data.exception.split(':')
        errorMsg = parts.length > 1 ? parts.slice(1).join(':').trim() : data.exception
      }
      if (!errorMsg) {
        errorMsg = `Request failed with status ${response.status}`
      }

      throw new Error(errorMsg)
    }

    return data.message
  } catch (error) {
    // Callers that render their own inline error state (e.g. the
    // assistant chat bubble) can pass { quiet: true } to skip the
    // global toast and avoid double-notifying the user.
    if (!quiet) {
      toast.error('Notice', {
        description: error.message || 'An error occurred',
      })
    }

    throw error
  }
}