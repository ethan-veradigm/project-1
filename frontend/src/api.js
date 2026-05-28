/**
 * Fetch the current run configuration defaults from the backend.
 * @returns {Promise<Object>}
 */
export async function fetchConfig() {
  const res = await fetch('/api/config')
  if (!res.ok) {
    throw new Error(`fetchConfig failed: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

/**
 * Fetch the list of available result files.
 * @returns {Promise<string[]>}
 */
export async function fetchFiles() {
  const res = await fetch('/api/files')
  if (!res.ok) {
    throw new Error(`fetchFiles failed: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

/**
 * Fetch parsed results for a specific result file.
 * @param {string} filename
 * @returns {Promise<{ summary: Object, results: Object[] }>}
 */
export async function fetchResults(filename) {
  const res = await fetch(`/api/results/${encodeURIComponent(filename)}`)
  if (!res.ok) {
    throw new Error(`fetchResults failed: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

/**
 * Start an evaluation run via SSE streaming.
 *
 * The server responds with a text/event-stream. Each event has the form:
 *   event: line\ndata: <json-encoded string>\n\n
 *   event: done\ndata: {"exit_code": 0}\n\n
 *
 * @param {Object}   config  - RunRequest fields
 * @param {Function} onLine  - called with each log line string
 * @param {Function} onDone  - called with the exit_code number when done
 */
export async function startRun(config, onLine, onDone) {
  const res = await fetch('/api/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`startRun failed: ${res.status} ${res.statusText} — ${text}`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // Process all complete lines in the buffer
    const lines = buffer.split('\n')
    // Keep the last (potentially incomplete) line in the buffer
    buffer = lines.pop()

    for (const raw of lines) {
      const line = raw.trimEnd()

      if (line.startsWith('data:')) {
        const dataStr = line.slice('data:'.length).trim()
        try {
          const parsed = JSON.parse(dataStr)
          if (parsed.done) {
            onDone(parsed.exit_code ?? 0)
          } else if (parsed.line != null) {
            onLine(String(parsed.line))
          }
        } catch {
          if (dataStr) onLine(dataStr)
        }
      }
    }
  }

  // Flush any remaining buffer content
  if (buffer.trim()) {
    const line = buffer.trim()
    if (line.startsWith('data:')) {
      const dataStr = line.slice('data:'.length).trim()
      try {
        const parsed = JSON.parse(dataStr)
        if (parsed.done) {
          onDone(parsed.exit_code ?? 0)
        } else if (parsed.line != null) {
          onLine(String(parsed.line))
        }
      } catch {
        if (dataStr) onLine(dataStr)
      }
    }
  }
}
