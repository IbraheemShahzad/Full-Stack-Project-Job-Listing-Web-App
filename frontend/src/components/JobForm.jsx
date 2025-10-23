import { useEffect, useMemo, useRef, useState } from 'react'
import PropTypes from 'prop-types'

const DEFAULTS = {
  title: '',
  company: '',
  city: '',
  country: '',
  location: '',
  job_type: '',
  posting_date: '',
  tags: [],
  job_url: '',
}

function sanitizeUrl(url) {
  if (!url) return ''
  const t = url.trim()
  if (!t) return ''
  return /^https?:\/\//i.test(t) ? t : `https://${t}`
}

export default function JobForm({
  open,
  editing = null,            // can be a job object or null
  initial = {},               // optional override for initial values
  submitting = false,
  onClose,
  onSubmit,
}) {
  const [error, setError] = useState('')
  const [form, setForm] = useState({
    ...DEFAULTS,
    ...(editing || initial || {}),
    tags: Array.isArray((editing || initial)?.tags) ? (editing || initial).tags : [],
  })

  const firstInputRef = useRef(null)
  const overlayRef = useRef(null)

  // keep in sync when editing/initial changes
  useEffect(() => {
    const seed = editing || initial || {}
    setForm({
      ...DEFAULTS,
      ...seed,
      tags: Array.isArray(seed.tags) ? seed.tags : [],
    })
    setError('')
  }, [editing, initial, open])

  // lock body scroll while open
  useEffect(() => {
    if (!open) return
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = prev }
  }, [open])

  // focus first input when opened
  useEffect(() => {
    if (open && firstInputRef.current) firstInputRef.current.focus()
  }, [open])

  // close on ESC
  useEffect(() => {
    if (!open) return
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  const setField = (key, value) => setForm(prev => ({ ...prev, [key]: value }))

  const tagsDisplay = useMemo(() => (form.tags || []).join(', '), [form.tags])

  const handleTagsChange = (raw) => {
    const arr = raw.split(',').map(s => s.trim()).filter(Boolean)
    setField('tags', Array.from(new Set(arr)))
  }

  const validate = (data) => {
    if (!data.title.trim()) return 'Title is required.'
    if (!data.company.trim()) return 'Company is required.'
    if (data.posting_date) {
      const iso = (data.posting_date || '').trim()
      if (iso && !/^\d{4}-\d{2}-\d{2}$/.test(iso)) return 'Posting date must be YYYY-MM-DD.'
      if (iso) {
        const d = new Date(iso)
        if (Number.isNaN(d.getTime())) return 'Posting date is invalid.'
      }
    }
    return null
  }

  const submit = async (e) => {
    e.preventDefault()
    setError('')

    const payload = {
      ...form,
      title: (form.title || '').trim(),
      company: (form.company || '').trim(),
      city: (form.city || '').trim(),
      country: (form.country || '').trim(),
      location: (form.location || '').trim(),
      job_type: form.job_type || '',
      posting_date: (form.posting_date || '').trim(),
      tags: (form.tags || []).map(t => t.trim()).filter(Boolean),
      job_url: sanitizeUrl(form.job_url),
    }

    const err = validate(payload)
    if (err) { setError(err); return }

    await onSubmit(payload)
  }

  const onBackdrop = (e) => {
    if (e.target === overlayRef.current) onClose()
  }

  if (!open) return null

  const isEditing = !!editing

  return (
    <div
      ref={overlayRef}
      onMouseDown={onBackdrop}
      className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50"
      aria-modal="true"
      role="dialog"
      aria-labelledby="job-modal-title"
    >
      <form onSubmit={submit} className="bg-white rounded-2xl shadow-xl w-full max-w-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 id="job-modal-title" className="text-lg font-semibold">
            {isEditing ? 'Edit job' : 'Add new job'}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-500 rounded focus:outline-none focus:ring-2 focus:ring-gray-400 px-1"
            aria-label="Close modal"
          >
            ✕
          </button>
        </div>

        {error ? (
          <div className="bg-red-50 text-red-700 text-sm p-2 rounded border border-red-200">{error}</div>
        ) : null}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <label className="text-sm">
            Title
            <input
              ref={firstInputRef}
              className="mt-1 w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form.title}
              onChange={(e) => setField('title', e.target.value)}
              required
            />
          </label>

          <label className="text-sm">
            Company
            <input
              className="mt-1 w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form.company}
              onChange={(e) => setField('company', e.target.value)}
              required
            />
          </label>

          <label className="text-sm">
            City
            <input
              className="mt-1 w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form.city || ''}
              onChange={(e) => setField('city', e.target.value)}
            />
          </label>

          <label className="text-sm">
            Country
            <input
              className="mt-1 w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form.country || ''}
              onChange={(e) => setField('country', e.target.value)}
            />
          </label>

          <label className="text-sm">
            Location (optional)
            <input
              className="mt-1 w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form.location || ''}
              onChange={(e) => setField('location', e.target.value)}
              placeholder="e.g., London, UK"
            />
          </label>

          <label className="text-sm">
            Job Type
            <select
              className="mt-1 w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form.job_type || ''}
              onChange={(e) => setField('job_type', e.target.value)}
            >
              <option value="">Select type</option>
              <option>Full-time</option>
              <option>Part-time</option>
              <option>Contract</option>
              <option>Internship</option>
            </select>
          </label>

          <label className="text-sm">
            Posting Date
            <input
              type="date"
              className="mt-1 w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form.posting_date || ''}
              onChange={(e) => setField('posting_date', e.target.value)}
              placeholder="2025-10-21"
            />
          </label>

          <label className="text-sm">
            Tags (comma separated)
            <input
              className="mt-1 w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={tagsDisplay}
              onChange={(e) => handleTagsChange(e.target.value)}
              placeholder="Life, Pricing"
            />
          </label>

          <label className="text-sm md:col-span-2">
            Job URL
            <input
              className="mt-1 w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form.job_url || ''}
              onChange={(e) => setField('job_url', e.target.value)}
              placeholder="https://example.com/job"
              inputMode="url"
            />
          </label>
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded border hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-400"
          >
            Cancel
          </button>
          <button
            disabled={submitting}
            className="px-4 py-2 rounded bg-blue-600 text-white disabled:opacity-60 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {submitting ? 'Saving…' : 'Save'}
          </button>
        </div>
      </form>
    </div>
  )
}

JobForm.propTypes = {
  open: PropTypes.bool.isRequired,
  editing: PropTypes.oneOfType([PropTypes.object, PropTypes.bool]),
  initial: PropTypes.object,
  submitting: PropTypes.bool,
  onClose: PropTypes.func.isRequired,
  onSubmit: PropTypes.func.isRequired,
}
