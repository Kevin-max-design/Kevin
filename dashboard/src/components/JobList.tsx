import { type Job } from '../api'
import './JobList.css'

interface JobListProps {
    jobs: Job[]
    onSelect: (job: Job) => void
    selectedId?: number
}

export function JobList({ jobs, onSelect, selectedId }: JobListProps) {
    const getScoreClass = (score: number) => {
        if (score >= 80) return 'excellent'
        if (score >= 60) return 'good'
        if (score >= 40) return 'average'
        return 'low'
    }

    const getStatusBadge = (status: string) => {
        const statusConfig: Record<string, { class: string; label: string }> = {
            new: { class: 'neutral', label: 'New' },
            matched: { class: 'info', label: 'Matched' },
            approved: { class: 'success', label: 'Approved' },
            applied: { class: 'info', label: 'Applied' },
            interview: { class: 'warning', label: 'Interview' },
            offer: { class: 'success', label: 'Offer' },
            rejected: { class: 'danger', label: 'Rejected' },
        }
        return statusConfig[status] || { class: 'neutral', label: status }
    }

    if (jobs.length === 0) {
        return (
            <div className="job-list-empty">
                <p>No jobs found. Try scraping for new opportunities!</p>
            </div>
        )
    }

    return (
        <div className="job-list">
            {jobs.map((job) => {
                const statusBadge = getStatusBadge(job.status)

                return (
                    <div
                        key={job.id}
                        className={`job-item ${selectedId === job.id ? 'selected' : ''}`}
                        onClick={() => onSelect(job)}
                    >
                        <div className="job-item-header">
                            <h3 className="job-title">{job.title}</h3>
                            <div className={`job-score score-${getScoreClass(job.match_score)}`}>
                                {job.match_score?.toFixed(0) || '—'}%
                            </div>
                        </div>

                        <div className="job-company">{job.company}</div>

                        <div className="job-meta">
                            <span className="platform-badge">{job.platform}</span>
                            <span className="job-location">{job.location || 'Remote'}</span>
                            <span className={`badge badge-${statusBadge.class}`}>
                                {statusBadge.label}
                            </span>
                        </div>

                        {job.matched_skills.length > 0 && (
                            <div className="job-skills">
                                {job.matched_skills.slice(0, 3).map((skill, i) => (
                                    <span key={i} className="skill-tag">{skill}</span>
                                ))}
                                {job.matched_skills.length > 3 && (
                                    <span className="skill-more">+{job.matched_skills.length - 3}</span>
                                )}
                            </div>
                        )}
                    </div>
                )
            })}
        </div>
    )
}
