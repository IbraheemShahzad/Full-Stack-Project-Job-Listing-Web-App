import { useEffect, useState } from 'react'
import PropTypes from 'prop-types'

export default function FilterBar({ query = {}, knownTags = [], onChange, onReset }) {
  const [local, setLocal] = useState({
    q: query.q || '',
    job_type: query.job_type || '',
    city: query.city || '',
    country: query.country || '',
    location: query.location || '',
    sort: query.sort || 'date_desc',
    tags: Array.isArray(query.tags) ? query.tags : [],
    tag_mode: query.tag_mode || 'any',
  })

  useEffect(() => {
    setLocal(prev => ({
      ...prev,
      ...query,
      tags: Array.isArray(query.tags) ? query.tags : prev.tags || [],
      tag_mode: query.tag_mode || prev.tag_mode || 'any',
    }))
  }, [query])

  const update = (patch) => setLocal(prev => ({ ...prev, ...patch }))

  const apply = () => {
    const params = { ...local }
    Object.keys(params).forEach(k => {
      const v = params[k]
      const emptyArray = Array.isArray(v) && v.length === 0
      const emptyString = v === '' || v === undefined || v === null
      if (emptyArray || emptyString) delete params[k]
    })
    onChange(params)
  }

  const toggleTag = (t) => {
    const set = new Set(local.tags || [])
    set.has(t) ? set.delete(t) : set.add(t)
    update({ tags: [...set] })
  }

  const resetAll = () => {
    setLocal({
      q: '', job_type: '', city: '', country: '', location: '',
      sort: 'date_desc', tags: [], tag_mode: 'any',
    })
    onReset()
  }

  return (
    <div className="bg-white rounded-xl shadow p-4 md:p-6 mb-4">
      <div className="grid grid-cols-1 md:grid-cols-6 gap-3">
        <input
          value={local.q}
          onChange={(e) => update({ q: e.target.value })}
          placeholder="Search title or company"
          className="col-span-1 md:col-span-2 border rounded-lg px-3 py-2"
          aria-label="Search"
        />

        <select
          value={local.job_type}
          onChange={(e) => update({ job_type: e.target.value })}
          className="border rounded-lg px-3 py-2"
          aria-label="Job type"
        >
          <option value="">All types</option>
          <option>Full-time</option>
          <option>Part-time</option>
          <option>Contract</option>
          <option>Internship</option>
        </select>

        <input
          value={local.city}
          onChange={(e) => update({ city: e.target.value })}
          placeholder="City"
          className="border rounded-lg px-3 py-2"
          aria-label="City"
        />

        <input
          value={local.country}
          onChange={(e) => update({ country: e.target.value })}
          placeholder="Country"
          className="border rounded-lg px-3 py-2"
          aria-label="Country"
        />

        <select
          value={local.sort}
          onChange={(e) => update({ sort: e.target.value })}
          className="border rounded-lg px-3 py-2"
          aria-label="Sort"
        >
          <option value="date_desc">Date: Newest</option>
          <option value="date_asc">Date: Oldest</option>
          <option value="title_asc">Title A→Z</option>
          <option value="company_asc">Company A→Z</option>
        </select>

        <div className="hidden md:block" />
      </div>

      {knownTags.length > 0 && (
        <div className="mt-3">
          <div className="flex items-center gap-2 flex-wrap">
            {knownTags.map((t) => {
              const active = (local.tags || []).includes(t)
              return (
                <button
                  key={t}
                  type="button"
                  onClick={() => toggleTag(t)}
                  className={`text-sm px-2 py-1 rounded-full border ${active ? 'bg-blue-600 text-white border-blue-600' : 'bg-gray-100'}`}
                  aria-pressed={active}
                >
                  {t}
                </button>
              )
            })}

            <select
              value={local.tag_mode}
              onChange={(e) => update({ tag_mode: e.target.value })}
              className="ml-auto border rounded-lg px-2 py-1 text-sm"
              aria-label="Tag match mode"
            >
              <option value="any">Match any</option>
              <option value="all">Match all</option>
            </select>
          </div>
        </div>
      )}

      <div className="mt-4 flex gap-2">
        <button type="button" onClick={apply} className="px-4 py-2 rounded-lg bg-blue-600 text-white">Apply</button>
        <button type="button" onClick={resetAll} className="px-4 py-2 rounded-lg border">Reset</button>
      </div>
    </div>
  )
}

FilterBar.propTypes = {
  query: PropTypes.shape({
    q: PropTypes.string,
    job_type: PropTypes.string,
    city: PropTypes.string,
    country: PropTypes.string,
    location: PropTypes.string,
    sort: PropTypes.oneOf(['date_desc','date_asc','title_asc','company_asc']),
    tags: PropTypes.arrayOf(PropTypes.string),
    tag_mode: PropTypes.oneOf(['any','all']),
  }),
  knownTags: PropTypes.arrayOf(PropTypes.string),
  onChange: PropTypes.func.isRequired,
  onReset: PropTypes.func.isRequired,
}
