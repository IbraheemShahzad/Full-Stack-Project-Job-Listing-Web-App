import { format } from 'date-fns'
import PropTypes from 'prop-types'

export default function JobCard({ job, onEdit, onDelete }) {
  const d = job?.posting_date ? format(new Date(job.posting_date), 'dd MMM yyyy') : '—'
  const location = job?.location || [job?.city, job?.country].filter(Boolean).join(', ')

  return (
    <div className="bg-white rounded-xl shadow p-5 flex flex-col">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{job.title}</h3>
          <p className="text-sm text-gray-600">
            {job.company} • {location || '—'}
          </p>
          <p className="text-xs text-gray-500">
            {job.job_type || '—'} • Posted {d}
          </p>
        </div>

        <div className="flex gap-2">
          <button onClick={() => onEdit(job)} className="text-blue-600 hover:underline text-sm">Edit</button>
          <button onClick={() => onDelete(job)} className="text-red-600 hover:underline text-sm">Delete</button>
        </div>
      </div>

      {Array.isArray(job.tags) && job.tags.length > 0 ? (
        <div className="mt-3 flex gap-2 flex-wrap">
          {job.tags.map((t) => (
            <span key={t} className="text-xs bg-gray-100 px-2 py-1 rounded-full">
              {t}
            </span>
          ))}
        </div>
      ) : null}

      {job.job_url ? (
        <a href={job.job_url} target="_blank" rel="noreferrer" className="mt-3 text-blue-600 text-sm hover:underline">
          View listing ↗
        </a>
      ) : null}
    </div>
  )
}

JobCard.propTypes = {
  job: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
    title: PropTypes.string.isRequired,
    company: PropTypes.string,
    city: PropTypes.string,
    country: PropTypes.string,
    location: PropTypes.string,
    posting_date: PropTypes.oneOfType([PropTypes.string, PropTypes.instanceOf(Date)]),
    job_type: PropTypes.string,
    tags: PropTypes.arrayOf(PropTypes.string),
    job_url: PropTypes.string,
  }).isRequired,
  onEdit: PropTypes.func.isRequired,
  onDelete: PropTypes.func.isRequired,
}
