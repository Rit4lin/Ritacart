import { useEffect, useState } from 'react'

type Health = { status: string }
type Status = 'checking' | 'ready' | 'error'

export default function App() {
  const [status, setStatus] = useState<Status>('checking')

  useEffect(() => {
    void fetch('/api/health')
      .then(async (response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        return response.json() as Promise<Health>
      })
      .then((data) => setStatus(data.status === 'ok' ? 'ready' : 'error'))
      .catch(() => setStatus('error'))
  }, [])

  const message = {
    checking: 'Comprobando conexión con el servidor…',
    ready: 'El backend responde correctamente.',
    error: 'No se ha podido contactar con el backend.',
  }[status]

  return (
    <main>
      <section aria-labelledby="title">
        <p className="eyebrow">RitaCart · fase inicial</p>
        <h1 id="title">Tu compra, lista para entenderla.</h1>
        <p className="intro">
          La aplicación está preparada. La importación de tickets y las estadísticas
          llegarán en las siguientes fases.
        </p>
        <p className={`health health--${status}`} role="status">
          <span aria-hidden="true" />
          {message}
        </p>
      </section>
    </main>
  )
}
