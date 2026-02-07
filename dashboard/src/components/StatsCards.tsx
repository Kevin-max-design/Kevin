import { type Stats } from '../api'
import './StatsCards.css'

interface StatsCardsProps {
    stats: Stats | null
}

export function StatsCards({ stats }: StatsCardsProps) {
    if (!stats) return null

    const cards = [
        {
            label: 'Total Jobs',
            value: Object.values(stats.status_counts).reduce((a, b) => a + b, 0),
            icon: '📋',
            color: 'neutral',
        },
        {
            label: 'Applied',
            value: stats.total_applied,
            icon: '📤',
            color: 'info',
        },
        {
            label: 'Interviews',
            value: stats.interview_count,
            icon: '🎤',
            color: 'warning',
            subtext: `${stats.interview_rate.toFixed(1)}% rate`,
        },
        {
            label: 'Offers',
            value: stats.offer_count,
            icon: '🎉',
            color: 'success',
            subtext: `${stats.offer_rate.toFixed(1)}% rate`,
        },
        {
            label: 'Avg Match',
            value: `${stats.average_match_score}%`,
            icon: '🎯',
            color: 'accent',
        },
    ]

    return (
        <div className="stats-cards">
            {cards.map((card, index) => (
                <div key={index} className={`stat-card stat-${card.color}`}>
                    <div className="stat-icon">{card.icon}</div>
                    <div className="stat-content">
                        <div className="stat-value">{card.value}</div>
                        <div className="stat-label">{card.label}</div>
                        {card.subtext && (
                            <div className="stat-subtext">{card.subtext}</div>
                        )}
                    </div>
                </div>
            ))}
        </div>
    )
}
