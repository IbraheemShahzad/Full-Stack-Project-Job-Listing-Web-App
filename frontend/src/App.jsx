import { useMemo, useState } from 'react'
import useJobs from './hooks/useJobs'
import FilterBar from './components/FilterBar'
import JobList from './components/JobList'
import JobForm from './components/JobForm'

export default function App() {
  const { query, data, loading, error, fetchJobs, addJob, updateJob, deleteJob, knownTags } = useJobs()
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState(null)

  const activeFilters = useMemo(() => {
    const f = []
    if (query.q) f.push(`q:"${query.q}"`)
    if (query.job_type) f.push(`type:${query.job_type}`)
    if (query.city) f.push(`city:${query.city}`)
    if (query.country) f.push(`country:${query.country}`)
    if (query.tags?.length) f.push(`tags:${query.tags.join('|')}${query.tag_mode==='all'?'(all)':''}`)
    return f
  }, [query])

  const onApplyFilters = (params) => fetchJobs({ ...params, page: 1 })
  const onReset = () => fetchJobs({ q: '', job_type: '', city: '', country: '', location: '', tags: [], tag_mode: 'any', sort: 'date_desc', page: 1 })

  const onDelete = async (job) => {
    if (confirm(`Delete job: ${job.title}?`)) {
      await deleteJob(job.id)
    }
  }

  const onEdit = (job) => { setEditing(job); setFormOpen(true) }
  const onAdd = () => { setEditing(null); setFormOpen(true) }

  const submitForm = async (payload) => {
    if (editing) return updateJob(editing.id, payload)
    return addJob(payload)
  }

  return (
    <div className="max-w-7xl mx-auto p-4 md:p-6">
      <header className="mb-4">
        <h1 className="text-2xl md:text-3xl font-bold">Bitbash Jobs</h1>
        <p className="text-gray-600">Actuarial job listings</p>
      </header>

      <FilterBar query={query} onChange={onApplyFilters} onReset={onReset} knownTags={knownTags} />

      <div className="flex items-center justify-between mb-3">
        <div className="text-sm text-gray-600">
          {activeFilters.length ? (
            <>Filters: <span className="font-medium">{activeFilters.join(' • ')}</span></>
          ) : <span>No filters</span>}
        </div>
        <button onClick={onAdd} className="px-4 py-2 rounded-lg bg-emerald-600 text-white">Add Job</button>
      </div>

      {error ? <div className="bg-red-50 text-red-700 p-2 rounded mb-3 text-sm">{error}</div> : null}
      {loading ? <div className="p-10 text-center text-gray-500">Loading…</div> : null}

      <JobList items={data.items} onEdit={onEdit} onDelete={onDelete} />

      <div className="mt-6 flex items-center justify-center gap-2">
        <button disabled={data.page <= 1} onClick={()=>fetchJobs({ page: data.page - 1 })} className="px-3 py-1 rounded border disabled:opacity-50">Prev</button>
        <span className="text-sm text-gray-600">Page {data.page}</span>
        <button disabled={(data.items?.length||0) < (data.page_size||12)} onClick={()=>fetchJobs({ page: data.page + 1 })} className="px-3 py-1 rounded border disabled:opacity-50">Next</button>
      </div>

      <JobForm open={formOpen} editing={editing} onClose={()=>setFormOpen(false)} onSubmit={submitForm} />
    </div>
  )
}
