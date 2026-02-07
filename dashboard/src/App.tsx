import { useState, useEffect, useCallback } from 'react'
import './App.css'
import {
  fetchStats, fetchJobs, fetchPendingApprovals, fetchActivity,
  approveJob, rejectJob, triggerScrape, triggerMatch, applyToJob,
  exportData,
  type Job, type Stats, type AuditLog
} from './api'

// Components
import { Sidebar } from './components/Sidebar'
import { Header } from './components/Header'
import { StatsCards } from './components/StatsCards'
import { JobList } from './components/JobList'
import { JobDetail } from './components/JobDetail'
import { ApprovalQueue } from './components/ApprovalQueue'
import { ActivityFeed } from './components/ActivityFeed'

type View = 'dashboard' | 'jobs' | 'approvals' | 'interview' | 'settings'

function App() {
  const [view, setView] = useState<View>('dashboard')
  const [stats, setStats] = useState<Stats | null>(null)
  const [jobs, setJobs] = useState<Job[]>([])
  const [pendingJobs, setPendingJobs] = useState<Job[]>([])
  const [activity, setActivity] = useState<AuditLog[]>([])
  const [selectedJob, setSelectedJob] = useState<Job | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [platformFilter, setPlatformFilter] = useState<string>('')

  // Load initial data
  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const [statsData, jobsData, pendingData, activityData] = await Promise.all([
        fetchStats(),
        fetchJobs({ status: statusFilter, platform: platformFilter, limit: 50 }),
        fetchPendingApprovals(),
        fetchActivity(20),
      ])

      setStats(statsData)
      setJobs(jobsData)
      setPendingJobs(pendingData)
      setActivity(activityData)
    } catch (err) {
      setError('Failed to load data. Make sure the API server is running.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [statusFilter, platformFilter])

  useEffect(() => {
    loadData()
  }, [loadData])

  // Action handlers
  const handleApprove = async (jobId: number, notes?: string) => {
    try {
      await approveJob(jobId, notes)
      await loadData()
    } catch (err) {
      console.error('Failed to approve:', err)
    }
  }

  const handleReject = async (jobId: number, reason?: string) => {
    try {
      await rejectJob(jobId, reason)
      await loadData()
    } catch (err) {
      console.error('Failed to reject:', err)
    }
  }

  const handleScrape = async () => {
    try {
      await triggerScrape()
      // Refresh after a delay
      setTimeout(loadData, 2000)
    } catch (err) {
      console.error('Failed to start scrape:', err)
    }
  }

  const handleMatch = async () => {
    try {
      await triggerMatch()
      await loadData()
    } catch (err) {
      console.error('Failed to run matching:', err)
    }
  }

  const handleApply = async (jobId: number) => {
    try {
      await applyToJob(jobId)
      await loadData()
    } catch (err) {
      console.error('Failed to apply:', err)
    }
  }

  const handleExport = async (format: 'json' | 'csv') => {
    try {
      const blob = await exportData(format, statusFilter)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `jobs_export.${format}`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Failed to export:', err)
    }
  }

  return (
    <div className="app">
      <Sidebar
        currentView={view}
        onViewChange={setView}
        pendingCount={pendingJobs.length}
      />

      <main className="main-content">
        <Header
          onScrape={handleScrape}
          onMatch={handleMatch}
          onExport={handleExport}
        />

        {error && (
          <div className="error-banner">
            {error}
            <button onClick={loadData}>Retry</button>
          </div>
        )}

        {loading && !stats ? (
          <div className="loading-container">
            <div className="spinner" />
            <p>Loading dashboard...</p>
          </div>
        ) : (
          <div className="content-area">
            {view === 'dashboard' && (
              <>
                <StatsCards stats={stats} />

                <div className="dashboard-grid">
                  <div className="dashboard-section">
                    <h2>Recent Jobs</h2>
                    <JobList
                      jobs={jobs.slice(0, 10)}
                      onSelect={setSelectedJob}
                      selectedId={selectedJob?.id}
                    />
                  </div>

                  <div className="dashboard-section">
                    <h2>Activity</h2>
                    <ActivityFeed activity={activity} />
                  </div>
                </div>
              </>
            )}

            {view === 'jobs' && (
              <div className="jobs-view">
                <div className="filters">
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                  >
                    <option value="">All Statuses</option>
                    <option value="new">New</option>
                    <option value="matched">Matched</option>
                    <option value="approved">Approved</option>
                    <option value="applied">Applied</option>
                    <option value="interview">Interview</option>
                    <option value="offer">Offer</option>
                    <option value="rejected">Rejected</option>
                  </select>

                  <select
                    value={platformFilter}
                    onChange={(e) => setPlatformFilter(e.target.value)}
                  >
                    <option value="">All Platforms</option>
                    <option value="linkedin">LinkedIn</option>
                    <option value="indeed">Indeed</option>
                    <option value="glassdoor">Glassdoor</option>
                    <option value="angellist">AngelList</option>
                    <option value="naukri">Naukri</option>
                  </select>
                </div>

                <div className="jobs-container">
                  <JobList
                    jobs={jobs}
                    onSelect={setSelectedJob}
                    selectedId={selectedJob?.id}
                  />

                  {selectedJob && (
                    <JobDetail
                      job={selectedJob}
                      onApprove={handleApprove}
                      onReject={handleReject}
                      onApply={handleApply}
                      onClose={() => setSelectedJob(null)}
                    />
                  )}
                </div>
              </div>
            )}

            {view === 'approvals' && (
              <ApprovalQueue
                jobs={pendingJobs}
                onApprove={handleApprove}
                onReject={handleReject}
                onSelect={setSelectedJob}
              />
            )}

            {view === 'interview' && (
              <div className="coming-soon">
                <h2>🎯 Interview Preparation</h2>
                <p>Select a job to generate customized interview preparation materials.</p>
              </div>
            )}

            {view === 'settings' && (
              <div className="coming-soon">
                <h2>⚙️ Settings</h2>
                <p>Configuration options coming soon.</p>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}

export default App
