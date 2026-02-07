"""
Job Application Agent - Main Entry Point

CLI interface for running the job application agent.
"""

import os
import sys
import logging
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
import schedule
import time as time_module

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import get_database
from src.scrapers import get_all_scrapers, get_scraper
from src.matching import JobMatcher, JobScorer
from src.applicator import ApplicationManager
from src.llm import OllamaClient

# Initialize CLI
app = typer.Typer(
    name="job-agent",
    help="AI-powered job application agent for ML/Data Science roles",
    add_completion=False,
)
console = Console()


def load_config() -> dict:
    """Load configuration file."""
    config_path = Path("config/config.yaml")
    if not config_path.exists():
        console.print("[red]Error: config/config.yaml not found![/red]")
        raise typer.Exit(1)
    
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_profile() -> dict:
    """Load user profile."""
    profile_path = Path("data/profile.yaml")
    if not profile_path.exists():
        console.print("[red]Error: data/profile.yaml not found![/red]")
        raise typer.Exit(1)
    
    with open(profile_path, "r") as f:
        return yaml.safe_load(f)


def setup_logging(debug: bool = False):
    """Configure logging."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("agent.log"),
        ]
    )


@app.command()
def scrape(
    platform: str = typer.Option(None, "--platform", "-p", help="Specific platform to scrape"),
    limit: int = typer.Option(50, "--limit", "-l", help="Max jobs per platform"),
):
    """Scrape jobs from job platforms."""
    config = load_config()
    profile = load_profile()
    config["scraping"]["max_jobs_per_platform"] = limit
    
    console.print(Panel.fit("🔍 [bold blue]Job Scraping[/bold blue]"))
    
    if platform:
        scrapers = [get_scraper(platform, config)]
    else:
        scrapers = get_all_scrapers(config)
    
    total_new = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for scraper in scrapers:
            task = progress.add_task(f"Scraping {scraper.platform_name}...", total=None)
            
            try:
                new_jobs = scraper.run(profile)
                total_new += new_jobs
                progress.update(task, description=f"[green]✓ {scraper.platform_name}: {new_jobs} new jobs")
            except Exception as e:
                progress.update(task, description=f"[red]✗ {scraper.platform_name}: {e}")
    
    console.print(f"\n[bold green]Total new jobs found: {total_new}[/bold green]")


@app.command()
def match():
    """Match jobs to your profile."""
    config = load_config()
    profile = load_profile()
    
    console.print(Panel.fit("🎯 [bold blue]Job Matching[/bold blue]"))
    
    matcher = JobMatcher(config)
    
    with console.status("Matching jobs..."):
        matches = matcher.match_all_jobs(profile)
    
    if not matches:
        console.print("[yellow]No matching jobs found. Try running 'scrape' first.[/yellow]")
        return
    
    # Display top matches
    table = Table(title=f"Top {min(10, len(matches))} Matches")
    table.add_column("Score", justify="right", style="cyan")
    table.add_column("Title", style="green")
    table.add_column("Company", style="yellow")
    table.add_column("Location")
    table.add_column("Platform")
    
    for match in matches[:10]:
        job = match["job"]
        table.add_row(
            f"{match['score']:.0f}%",
            job["title"][:40],
            job["company"][:25],
            (job.get("location") or "")[:20],
            job["platform"],
        )
    
    console.print(table)
    console.print(f"\n[bold]Total matches: {len(matches)}[/bold]")


@app.command()
def apply(
    job_id: int = typer.Option(None, "--job", "-j", help="Specific job ID to apply to"),
    batch: bool = typer.Option(False, "--batch", "-b", help="Apply to multiple jobs"),
    limit: int = typer.Option(10, "--limit", "-l", help="Max applications for batch"),
    dry_run: bool = typer.Option(True, "--dry-run/--submit", help="Dry run mode"),
):
    """Apply to jobs."""
    config = load_config()
    profile = load_profile()
    config["application"]["dry_run"] = dry_run
    
    mode = "[yellow]DRY RUN[/yellow]" if dry_run else "[red]LIVE[/red]"
    console.print(Panel.fit(f"📝 [bold blue]Job Application[/bold blue] ({mode})"))
    
    manager = ApplicationManager(config)
    
    if job_id:
        # Single application
        materials = manager.prepare_application(job_id, profile)
        
        if "error" in materials:
            console.print(f"[red]{materials['error']}[/red]")
            return
        
        console.print(f"\n[bold]Job:[/bold] {materials['job']['title']} at {materials['job']['company']}")
        console.print(f"[bold]Match Score:[/bold] {materials['match_score']:.0f}%")
        console.print(f"\n[bold]Cover Letter Preview:[/bold]\n{materials['cover_letter'][:500]}...")
        
        if typer.confirm("\nProceed with application?"):
            success = manager.apply_single(job_id, profile)
            if success:
                console.print("[green]✓ Application submitted![/green]")
            else:
                console.print("[red]✗ Application failed[/red]")
    
    elif batch:
        # Batch application
        stats = manager.apply_batch(profile, limit)
        
        console.print(f"\n[bold]Results:[/bold]")
        console.print(f"  ✓ Submitted: {stats['submitted']}")
        console.print(f"  ✗ Failed: {stats['failed']}")
        console.print(f"  ⊘ Skipped: {stats.get('skipped', 0)}")
    
    else:
        console.print("[yellow]Specify --job ID or --batch flag[/yellow]")


@app.command()
def stats():
    """Show application statistics."""
    config = load_config()
    manager = ApplicationManager(config)
    
    stats = manager.get_application_stats()
    
    console.print(Panel.fit("📊 [bold blue]Statistics[/bold blue]"))
    
    table = Table(show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="green")
    
    table.add_row("Total Jobs Scraped", str(stats["total_jobs"]))
    table.add_row("Applications Submitted", str(stats["applied"]))
    table.add_row("Pending Jobs", str(stats["pending"]))
    table.add_row("Today's Applications", str(stats["today_applications"]))
    table.add_row("This Week's Applications", str(stats["week_applications"]))
    table.add_row("Remaining Today", str(stats["remaining_today"]))
    
    console.print(table)


@app.command()
def dashboard():
    """Start the web dashboard."""
    import uvicorn
    
    config = load_config()
    dashboard_config = config.get("dashboard", {})
    
    host = dashboard_config.get("host", "127.0.0.1")
    port = dashboard_config.get("port", 8000)
    
    console.print(f"[bold blue]Starting dashboard at http://{host}:{port}[/bold blue]")
    
    uvicorn.run("src.api.main:app", host=host, port=port, reload=True)


@app.command()
def auto(
    interval: int = typer.Option(60, "--interval", "-i", help="Scraping interval in minutes"),
):
    """Run in fully automatic mode."""
    config = load_config()
    profile = load_profile()
    
    console.print(Panel.fit("🤖 [bold green]AUTO MODE[/bold green]"))
    console.print(f"Scraping every {interval} minutes, applying to top matches")
    console.print("[yellow]Press Ctrl+C to stop[/yellow]\n")
    
    def job_cycle():
        console.print(f"\n[dim]{time_module.strftime('%H:%M:%S')}[/dim] Running job cycle...")
        
        # Scrape
        scrapers = get_all_scrapers(config)
        for scraper in scrapers:
            try:
                scraper.run(profile)
            except Exception as e:
                console.print(f"[red]Scraper error: {e}[/red]")
        
        # Match and apply
        manager = ApplicationManager(config)
        stats = manager.apply_batch(profile)
        
        console.print(f"  Applied: {stats['submitted']}, Failed: {stats['failed']}")
    
    # Run immediately
    job_cycle()
    
    # Schedule periodic runs
    schedule.every(interval).minutes.do(job_cycle)
    
    try:
        while True:
            schedule.run_pending()
            time_module.sleep(60)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped by user[/yellow]")


@app.command()
def check():
    """Check system requirements."""
    console.print(Panel.fit("🔧 [bold blue]System Check[/bold blue]"))
    
    checks = []
    
    # Check config
    try:
        config = load_config()
        checks.append(("Config file", True, ""))
    except Exception as e:
        checks.append(("Config file", False, str(e)))
        config = {}
    
    # Check profile
    try:
        profile = load_profile()
        name = profile.get("personal", {}).get("name", "")
        checks.append(("User profile", bool(name), "Name not set" if not name else ""))
    except Exception as e:
        checks.append(("User profile", False, str(e)))
    
    # Check Ollama
    try:
        client = OllamaClient(config)
        available = client.is_available()
        checks.append(("Ollama LLM", available, "Run: ollama serve" if not available else ""))
    except Exception as e:
        checks.append(("Ollama LLM", False, str(e)))
    
    # Check database
    try:
        db = get_database()
        checks.append(("Database", True, ""))
    except Exception as e:
        checks.append(("Database", False, str(e)))
    
    # Display results
    table = Table()
    table.add_column("Component")
    table.add_column("Status")
    table.add_column("Note")
    
    for name, ok, note in checks:
        status = "[green]✓[/green]" if ok else "[red]✗[/red]"
        table.add_row(name, status, note)
    
    console.print(table)
    
    all_ok = all(c[1] for c in checks)
    if all_ok:
        console.print("\n[green]All checks passed! Ready to run.[/green]")
    else:
        console.print("\n[yellow]Some checks failed. Fix issues before running.[/yellow]")


if __name__ == "__main__":
    setup_logging()
    app()
