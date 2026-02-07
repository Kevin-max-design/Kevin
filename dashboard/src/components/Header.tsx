import { useState } from 'react'
import './Header.css'

interface HeaderProps {
    onScrape: () => void
    onMatch: () => void
    onExport: (format: 'json' | 'csv') => void
}

export function Header({ onScrape, onMatch, onExport }: HeaderProps) {
    const [scraping, setScraping] = useState(false)
    const [matching, setMatching] = useState(false)

    const handleScrape = async () => {
        setScraping(true)
        await onScrape()
        setTimeout(() => setScraping(false), 3000)
    }

    const handleMatch = async () => {
        setMatching(true)
        await onMatch()
        setMatching(false)
    }

    return (
        <header className="header">
            <div className="header-title">
                <h1>AI Job Application Agent</h1>
                <p>Automated job search and application management</p>
            </div>

            <div className="header-actions">
                <button
                    className="btn btn-secondary"
                    onClick={() => onExport('csv')}
                >
                    📥 Export CSV
                </button>

                <button
                    className="btn btn-secondary"
                    onClick={handleMatch}
                    disabled={matching}
                >
                    {matching ? (
                        <>
                            <span className="spinner small"></span>
                            Matching...
                        </>
                    ) : (
                        <>🎯 Run Matching</>
                    )}
                </button>

                <button
                    className="btn btn-primary"
                    onClick={handleScrape}
                    disabled={scraping}
                >
                    {scraping ? (
                        <>
                            <span className="spinner small"></span>
                            Scraping...
                        </>
                    ) : (
                        <>🔍 Scrape Jobs</>
                    )}
                </button>
            </div>
        </header>
    )
}
