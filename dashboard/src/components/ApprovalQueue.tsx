import { type Job } from '../api'
import './ApprovalQueue.css'

interface ApprovalQueueProps {
    jobs: Job[]
    onApprove: (jobId: number, notes?: string) => void
    onReject: (jobId: number, reason?: string) => void
    onSelect: (job: Job) => void
}

export function ApprovalQueue({ jobs, onApprove, onReject, onSelect }: ApprovalQueueProps) {
    if (jobs.length === 0) {
        return (
            <div className="approval-empty">
                <div className="empty-icon">✅</div>
                <h2>All Caught Up!</h2>
                <p>No jobs pending approval. Run a new scrape to find more opportunities.</p>
            </div>
        )
    }

    return (
        <div className="approval-queue">
            <div className="approval-header">
                <h2>🔍 Pending Approvals</h2>
                <p>{jobs.length} jobs waiting for your review</p>
            </div>

            <div className="approval-list">
                {jobs.map((job) => (
                    <div key={job.id} className="approval-card">
                        <div className="approval-card-main" onClick={() => onSelect(job)}>
                            <div className="approval-score-badge">
                                <span className="score-value">{job.match_score?.toFixed(0) || 0}%</span>
                                <span className="score-label">Match</span>
                            </div>

                            <div className="approval-info">
                                <h3>{job.title}</h3>
                                <p className="company">{job.company}</p>
                                <div className="meta">
                                    <span className="platform">{job.platform}</span>
                                    <span className="location">{job.location || 'Remote'}</span>
                                    {job.is_easy_apply && (
                                        <span className="easy-apply">⚡ Easy Apply</span>
                                    )}
                                </div>

                                {job.matched_skills.length > 0 && (
                                    <div className="skills-preview">
                                        {job.matched_skills.slice(0, 4).map((skill, i) => (
                                            <span key={i} className="skill">{skill}</span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>

                        <div className="approval-actions">
                            <button
                                className="action-btn reject"
                                onClick={() => onReject(job.id)}
                                title="Reject"
                            >
                                ✕
                            </button>
                            <button
                                className="action-btn approve"
                                onClick={() => onApprove(job.id)}
                                title="Approve"
                            >
                                ✓
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}
