import { useState } from 'react'
import { type Job } from '../api'
import './JobDetail.css'

interface JobDetailProps {
    job: Job
    onApprove: (jobId: number, notes?: string) => void
    onReject: (jobId: number, reason?: string) => void
    onApply: (jobId: number) => void
    onClose: () => void
}

export function JobDetail({ job, onApprove, onReject, onApply, onClose }: JobDetailProps) {
    const [notes, setNotes] = useState('')
    const [loading, setLoading] = useState(false)

    const handleApprove = async () => {
        setLoading(true)
        await onApprove(job.id, notes)
        setLoading(false)
    }

    const handleReject = async () => {
        setLoading(true)
        await onReject(job.id, notes)
        setLoading(false)
    }

    const handleApply = async () => {
        setLoading(true)
        await onApply(job.id)
        setLoading(false)
    }

    return (
        <div className="job-detail">
            <div className="job-detail-header">
                <div>
                    <h2>{job.title}</h2>
                    <p className="company">{job.company}</p>
                </div>
                <button className="close-btn" onClick={onClose}>✕</button>
            </div>

            <div className="job-detail-content">
                {/* Score Section */}
                <div className="score-section">
                    <div className="score-circle">
                        <svg viewBox="0 0 100 100">
                            <circle
                                className="score-bg"
                                cx="50"
                                cy="50"
                                r="45"
                            />
                            <circle
                                className="score-progress"
                                cx="50"
                                cy="50"
                                r="45"
                                style={{
                                    strokeDasharray: `${job.match_score * 2.83} 283`,
                                }}
                            />
                        </svg>
                        <div className="score-text">
                            <span className="score-value">{job.match_score?.toFixed(0) || 0}</span>
                            <span className="score-label">Match</span>
                        </div>
                    </div>
                </div>

                {/* Details Grid */}
                <div className="details-grid">
                    <div className="detail-item">
                        <span className="detail-label">Location</span>
                        <span className="detail-value">{job.location || 'Not specified'}</span>
                    </div>
                    <div className="detail-item">
                        <span className="detail-label">Work Mode</span>
                        <span className="detail-value">{job.work_mode || 'Not specified'}</span>
                    </div>
                    <div className="detail-item">
                        <span className="detail-label">Platform</span>
                        <span className="detail-value">{job.platform}</span>
                    </div>
                    <div className="detail-item">
                        <span className="detail-label">Job Type</span>
                        <span className="detail-value">{job.job_type || 'Full-time'}</span>
                    </div>
                </div>

                {/* Skills */}
                {job.matched_skills.length > 0 && (
                    <div className="skills-section">
                        <h4>Matched Skills</h4>
                        <div className="skill-tags">
                            {job.matched_skills.map((skill, i) => (
                                <span key={i} className="skill-tag matched">{skill}</span>
                            ))}
                        </div>
                    </div>
                )}

                {job.missing_skills.length > 0 && (
                    <div className="skills-section">
                        <h4>Skill Gaps</h4>
                        <div className="skill-tags">
                            {job.missing_skills.map((skill, i) => (
                                <span key={i} className="skill-tag missing">{skill}</span>
                            ))}
                        </div>
                    </div>
                )}

                {/* Description */}
                {job.description && (
                    <div className="description-section">
                        <h4>Job Description</h4>
                        <p>{job.description.slice(0, 500)}...</p>
                    </div>
                )}

                {/* Notes Input */}
                <div className="notes-section">
                    <textarea
                        placeholder="Add notes (optional)..."
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                    />
                </div>

                {/* Actions */}
                <div className="action-buttons">
                    <a
                        href={job.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn btn-secondary"
                    >
                        🔗 View Original
                    </a>

                    {job.status === 'matched' && !job.is_approved && (
                        <>
                            <button
                                className="btn btn-danger"
                                onClick={handleReject}
                                disabled={loading}
                            >
                                ✕ Reject
                            </button>
                            <button
                                className="btn btn-success"
                                onClick={handleApprove}
                                disabled={loading}
                            >
                                ✓ Approve
                            </button>
                        </>
                    )}

                    {job.is_approved && job.status !== 'applied' && (
                        <button
                            className="btn btn-primary"
                            onClick={handleApply}
                            disabled={loading}
                        >
                            📤 Apply Now
                        </button>
                    )}
                </div>
            </div>
        </div>
    )
}
