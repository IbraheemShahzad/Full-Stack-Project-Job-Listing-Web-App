import PropTypes from 'prop-types'
import JobCard from './JobCard'

export default function JobList({ items = [], onEdit, onDelete }) {
  if (!items?.length) {
    return <div className="text-center text-gray-500 p-10">No jobs found.</div>
  }
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {items.map((j) => (
        <JobCard key={j.id} job={j} onEdit={onEdit} onDelete={onDelete} />
      ))}
    </div>
  )
}

JobList.propTypes = {
  items: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
      title: PropTypes.string.isRequired,
      company: PropTypes.string,
      city: PropTypes.string,
      country: PropTypes.string,
      location: PropTypes.string,
      posting_date: PropTypes.oneOfType([PropTypes.string, PropTypes.instanceOf(Date)]),
      job_type: PropTypes.string,
      tags: PropTypes.arrayOf(PropTypes.string),
      job_url: PropTypes.string,
    })
  ).isRequired,
  onEdit: PropTypes.func.isRequired,
  onDelete: PropTypes.func.isRequired,
}
