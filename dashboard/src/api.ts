const API_BASE = 'http://localhost:8000/api';

export interface Job {
    id: number;
    title: string;
    company: string;
    location: string;
    description?: string;
    url: string;
    platform: string;
    job_type: string;
    work_mode: string;
    match_score: number;
    semantic_score?: number;
    matched_skills: string[];
    missing_skills: string[];
    status: string;
    is_approved: boolean;
    is_easy_apply: boolean;
    posted_date?: string;
    scraped_at?: string;
    applied_at?: string;
}

export interface Application {
    id: number;
    job_id: number;
    status: string;
    application_method: string;
    created_at: string;
    applied_at?: string;
    response_received: boolean;
    notes?: string;
}

export interface Stats {
    status_counts: Record<string, number>;
    recent_applied: number;
    total_applied: number;
    interview_count: number;
    offer_count: number;
    interview_rate: number;
    offer_rate: number;
    platform_counts: Record<string, number>;
    average_match_score: number;
}

export interface AuditLog {
    id: number;
    action: string;
    entity_type: string;
    entity_id: number;
    details: Record<string, any>;
    status: string;
    created_at: string;
    job_title?: string;
    company?: string;
}

export interface CoverLetterPreview {
    cover_letter: string;
    job: Job;
}

// API Functions
export async function fetchStats(): Promise<Stats> {
    const response = await fetch(`${API_BASE}/stats`);
    if (!response.ok) throw new Error('Failed to fetch stats');
    return response.json();
}

export async function fetchJobs(params: {
    status?: string;
    platform?: string;
    min_score?: number;
    limit?: number;
}): Promise<Job[]> {
    const searchParams = new URLSearchParams();
    if (params.status) searchParams.append('status', params.status);
    if (params.platform) searchParams.append('platform', params.platform);
    if (params.min_score) searchParams.append('min_score', params.min_score.toString());
    if (params.limit) searchParams.append('limit', params.limit.toString());

    const response = await fetch(`${API_BASE}/jobs?${searchParams}`);
    if (!response.ok) throw new Error('Failed to fetch jobs');
    return response.json();
}

export async function fetchJob(id: number): Promise<Job> {
    const response = await fetch(`${API_BASE}/jobs/${id}`);
    if (!response.ok) throw new Error('Failed to fetch job');
    return response.json();
}

export async function fetchPendingApprovals(): Promise<Job[]> {
    const response = await fetch(`${API_BASE}/jobs/pending`);
    if (!response.ok) throw new Error('Failed to fetch pending approvals');
    return response.json();
}

export async function approveJob(jobId: number, notes?: string): Promise<void> {
    const response = await fetch(`${API_BASE}/jobs/${jobId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notes }),
    });
    if (!response.ok) throw new Error('Failed to approve job');
}

export async function rejectJob(jobId: number, reason?: string): Promise<void> {
    const response = await fetch(`${API_BASE}/jobs/${jobId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
    });
    if (!response.ok) throw new Error('Failed to reject job');
}

export async function triggerScrape(platforms?: string[]): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE}/scrape`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ platforms }),
    });
    if (!response.ok) throw new Error('Failed to start scrape');
    return response.json();
}

export async function triggerMatch(): Promise<{ message: string; matched: number }> {
    const response = await fetch(`${API_BASE}/match`, {
        method: 'POST',
    });
    if (!response.ok) throw new Error('Failed to run matching');
    return response.json();
}

export async function applyToJob(jobId: number): Promise<{ success: boolean; message: string }> {
    const response = await fetch(`${API_BASE}/jobs/${jobId}/apply`, {
        method: 'POST',
    });
    if (!response.ok) throw new Error('Failed to apply');
    return response.json();
}

export async function previewCoverLetter(jobId: number): Promise<CoverLetterPreview> {
    const response = await fetch(`${API_BASE}/jobs/${jobId}/cover-letter`);
    if (!response.ok) throw new Error('Failed to generate cover letter');
    return response.json();
}

export async function fetchActivity(limit: number = 20): Promise<AuditLog[]> {
    const response = await fetch(`${API_BASE}/activity?limit=${limit}`);
    if (!response.ok) throw new Error('Failed to fetch activity');
    return response.json();
}

export async function exportData(format: 'json' | 'csv', status?: string): Promise<Blob> {
    const params = new URLSearchParams({ format });
    if (status) params.append('status', status);

    const response = await fetch(`${API_BASE}/export?${params}`);
    if (!response.ok) throw new Error('Failed to export data');
    return response.blob();
}

export async function generateInterviewPrep(jobId: number): Promise<any> {
    const response = await fetch(`${API_BASE}/jobs/${jobId}/interview-prep`, {
        method: 'POST',
    });
    if (!response.ok) throw new Error('Failed to generate interview prep');
    return response.json();
}
