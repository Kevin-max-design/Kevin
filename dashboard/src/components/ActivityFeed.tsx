import { type AuditLog } from '../api'
import './ActivityFeed.css'

interface ActivityFeedProps {
    activity: AuditLog[]
}

export function ActivityFeed({ activity }: ActivityFeedProps) {
    const getActionIcon = (action: string) => {
        const icons: Record<string, string> = {
            'status_change': '🔄',
            'application_attempt': '📤',
            'job_scraped': '🔍',
            'job_matched': '🎯',
            'cover_letter_generated': '📝',
            'resume_tailored': '📄',
            'interview_prep_generated': '🎯',
            default: '📌',
        }
        return icons[action] || icons.default
    }

    const formatTime = (dateStr: string) => {
        const date = new Date(dateStr)
        const now = new Date()
        const diff = now.getTime() - date.getTime()

        const minutes = Math.floor(diff / 60000)
        const hours = Math.floor(diff / 3600000)
        const days = Math.floor(diff / 86400000)

        if (minutes < 1) return 'Just now'
        if (minutes < 60) return `${minutes}m ago`
        if (hours < 24) return `${hours}h ago`
        if (days < 7) return `${days}d ago`

        return date.toLocaleDateString()
    }

    const formatAction = (log: AuditLog) => {
        switch (log.action) {
            case 'status_change':
                return `Status changed to ${log.details?.new_status || 'unknown'}`
            case 'application_attempt':
                return log.status === 'success' ? 'Applied successfully' : 'Application failed'
            case 'job_matched':
                return 'Job matched with profile'
            default:
                return log.action.replace(/_/g, ' ')
        }
    }

    if (activity.length === 0) {
        return (
            <div className="activity-empty">
                <p>No recent activity</p>
            </div>
        )
    }

    return (
        <div className="activity-feed">
            {activity.map((log) => (
                <div key={log.id} className={`activity-item ${log.status}`}>
                    <div className="activity-icon">{getActionIcon(log.action)}</div>
                    <div className="activity-content">
                        <div className="activity-text">
                            <span className="activity-action">{formatAction(log)}</span>
                            {log.job_title && (
                                <span className="activity-job">
                                    {log.job_title} at {log.company}
                                </span>
                            )}
                        </div>
                        <div className="activity-time">{formatTime(log.created_at)}</div>
                    </div>
                </div>
            ))}
        </div>
    )
}
