import { useCallback, useEffect, useMemo, useState } from 'react'
import api from '../api'


export default function useJobs(initialQuery = {}) {
const [query, setQuery] = useState({ page: 1, page_size: 12, sort: 'date_desc', tag_mode: 'any', ...initialQuery })
const [data, setData] = useState({ items: [], total: 0, page: 1, page_size: 12 })
const [loading, setLoading] = useState(false)
const [error, setError] = useState(null)


const fetchJobs = useCallback(async (overrides = {}) => {
setLoading(true); setError(null)
const params = { ...query, ...overrides }
try {
const res = await api.get('/jobs', { params })
setData(res.data)
setQuery(params)
} catch (e) {
setError(e.response?.data?.message || e.message)
} finally {
setLoading(false)
}
}, [query])


useEffect(() => {
  fetchJobs();           // initial load only
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, []);



const addJob = useCallback(async (payload) => {
const res = await api.post('/jobs', payload)
await fetchJobs({ page: 1 })
return res.data
}, [fetchJobs])


const updateJob = useCallback(async (id, patch) => {
const res = await api.patch(`/jobs/${id}`, patch)
await fetchJobs()
return res.data
}, [fetchJobs])


const deleteJob = useCallback(async (id) => {
await api.delete(`/jobs/${id}`)
await fetchJobs()
}, [fetchJobs])


const knownTags = useMemo(() => {
const map = new Map()
for (const it of data.items) {
for (const t of (it.tags || [])) {
map.set(t, (map.get(t) || 0) + 1)
}
}
return Array.from(map.entries()).sort((a,b)=>b[1]-a[1]).slice(0,20).map(([k])=>k)
}, [data.items])


return { query, setQuery, data, loading, error, fetchJobs, addJob, updateJob, deleteJob, knownTags }
}