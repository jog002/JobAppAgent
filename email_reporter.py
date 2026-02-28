"""Email reporting module for job search results."""

import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class EmailReporter:
    """Sends job search reports via email."""

    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        sender_email: str,
        sender_password: str,
        recipient_email: str,
        use_tls: bool = True
    ):
        """Initialize email reporter.

        Args:
            smtp_server: SMTP server address (e.g., smtp.gmail.com)
            smtp_port: SMTP port (587 for TLS, 465 for SSL)
            sender_email: Email address to send from
            sender_password: App password or email password
            recipient_email: Email address to send reports to
            use_tls: Whether to use TLS (default True)
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.recipient_email = recipient_email
        self.use_tls = use_tls

    def send_report(
        self,
        run_number: int,
        new_jobs: list,
        top_jobs_overall: list,
        stats: dict,
        success: bool = True,
        error: Optional[str] = None
    ) -> bool:
        """Send job search report via email.

        Args:
            run_number: The search run number
            new_jobs: List of new jobs from this run (top 10)
            top_jobs_overall: List of top jobs overall (top 10)
            stats: Dictionary with run statistics
            success: Whether the run was successful
            error: Error message if run failed

        Returns:
            True if email sent successfully, False otherwise.
        """
        try:
            # Build email content
            subject = self._build_subject(run_number, success, len(new_jobs))
            html_body = self._build_html_body(
                run_number, new_jobs, top_jobs_overall, stats, success, error
            )
            text_body = self._build_text_body(
                run_number, new_jobs, top_jobs_overall, stats, success, error
            )

            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = self.recipient_email

            # Attach both plain text and HTML versions
            message.attach(MIMEText(text_body, "plain"))
            message.attach(MIMEText(html_body, "html"))

            # Send email
            context = ssl.create_default_context()

            if self.use_tls:
                # Use STARTTLS (port 587)
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls(context=context)
                    server.login(self.sender_email, self.sender_password)
                    server.sendmail(
                        self.sender_email,
                        self.recipient_email,
                        message.as_string()
                    )
            else:
                # Use SSL (port 465)
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context) as server:
                    server.login(self.sender_email, self.sender_password)
                    server.sendmail(
                        self.sender_email,
                        self.recipient_email,
                        message.as_string()
                    )

            logger.info(f"Email report sent successfully to {self.recipient_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email report: {e}")
            return False

    def _build_subject(self, run_number: int, success: bool, new_jobs_count: int) -> str:
        """Build email subject line."""
        status = "Success" if success else "Failed"
        date = datetime.now().strftime("%Y-%m-%d")
        return f"Job Search Report #{run_number} - {status} - {new_jobs_count} New Jobs ({date})"

    def _build_html_body(
        self,
        run_number: int,
        new_jobs: list,
        top_jobs_overall: list,
        stats: dict,
        success: bool,
        error: Optional[str]
    ) -> str:
        """Build HTML email body."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
                .content {{ padding: 30px; }}
                .section {{ margin-bottom: 30px; }}
                .section-title {{ font-size: 18px; font-weight: 600; color: #333; margin-bottom: 15px; border-bottom: 2px solid #667eea; padding-bottom: 8px; }}
                .job-card {{ background: #f8f9fa; border-radius: 6px; padding: 15px; margin-bottom: 12px; border-left: 4px solid #667eea; }}
                .job-card.high-score {{ border-left-color: #28a745; }}
                .job-card.mid-score {{ border-left-color: #ffc107; }}
                .job-title {{ font-weight: 600; color: #333; margin-bottom: 5px; }}
                .job-company {{ color: #666; margin-bottom: 8px; }}
                .job-meta {{ font-size: 13px; color: #888; }}
                .job-score {{ display: inline-block; padding: 4px 10px; border-radius: 12px; font-weight: 600; font-size: 13px; }}
                .score-high {{ background: #d4edda; color: #155724; }}
                .score-mid {{ background: #fff3cd; color: #856404; }}
                .score-low {{ background: #f8d7da; color: #721c24; }}
                .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }}
                .stat-card {{ background: #f8f9fa; border-radius: 6px; padding: 15px; text-align: center; }}
                .stat-value {{ font-size: 24px; font-weight: 700; color: #667eea; }}
                .stat-label {{ font-size: 12px; color: #666; text-transform: uppercase; margin-top: 5px; }}
                .footer {{ background: #f8f9fa; padding: 20px 30px; border-radius: 0 0 8px 8px; font-size: 12px; color: #666; text-align: center; }}
                a {{ color: #667eea; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                .error-box {{ background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; padding: 15px; border-radius: 6px; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Job Search Report #{run_number}</h1>
                    <p>{timestamp}</p>
                </div>
                <div class="content">
        """

        # Error section if failed
        if not success and error:
            html += f"""
                    <div class="error-box">
                        <strong>Error:</strong> {error}
                    </div>
            """

        # New jobs from this run (shown first)
        if new_jobs:
            html += """
                    <div class="section">
                        <div class="section-title">New Jobs from This Run</div>
            """
            for job in new_jobs[:10]:
                html += self._job_card_html(job)
            html += """
                    </div>
            """

        # Top jobs overall
        if top_jobs_overall:
            html += """
                    <div class="section">
                        <div class="section-title">Top Jobs Overall</div>
            """
            for job in top_jobs_overall[:10]:
                html += self._job_card_html(job)
            html += """
                    </div>
            """

        # Stats section (at the end)
        html += """
                    <div class="section">
                        <div class="section-title">Run Statistics</div>
                        <div class="stats-grid">
        """

        prompt_tokens = stats.get('prompt_tokens', 0)
        completion_tokens = stats.get('completion_tokens', 0)
        est_cost = (prompt_tokens * 2 + completion_tokens * 8) / 1000000

        stats_items = [
            ("Jobs Found", stats.get('jobs_found', 0)),
            ("New Jobs", stats.get('jobs_new', 0)),
            ("Duration", f"{stats.get('duration_seconds', 0):.1f}s"),
            ("API Calls", stats.get('api_calls', 0)),
            ("Prompt Tokens", f"{prompt_tokens:,}"),
            ("Completion Tokens", f"{completion_tokens:,}"),
            ("Est. Cost", f"${est_cost:.4f}"),
        ]

        for label, value in stats_items:
            html += f"""
                            <div class="stat-card">
                                <div class="stat-value">{value}</div>
                                <div class="stat-label">{label}</div>
                            </div>
            """

        html += """
                        </div>
                    </div>
        """

        # Footer
        html += """
                </div>
                <div class="footer">
                    Generated by Multi-Source Job Agent
                </div>
            </div>
        </body>
        </html>
        """

        return html

    def _job_card_html(self, job: dict) -> str:
        """Generate HTML for a single job card."""
        score = job.get('score', 0) or 0
        title = job.get('title', 'Unknown')
        company = job.get('company', 'Unknown')
        location = job.get('location', 'Unknown')
        url = job.get('url', '#')
        salary_min = job.get('salary_min')
        salary_max = job.get('salary_max')

        # Determine score class
        if score >= 75:
            score_class = "score-high"
            card_class = "job-card high-score"
        elif score >= 60:
            score_class = "score-mid"
            card_class = "job-card mid-score"
        else:
            score_class = "score-low"
            card_class = "job-card"

        # Format salary
        salary_str = ""
        if salary_min and salary_max:
            salary_str = f"${salary_min:,.0f} - ${salary_max:,.0f}"
        elif salary_min:
            salary_str = f"${salary_min:,.0f}+"
        elif salary_max:
            salary_str = f"Up to ${salary_max:,.0f}"

        return f"""
                        <div class="{card_class}">
                            <div class="job-title">
                                <a href="{url}">{title}</a>
                                <span class="job-score {score_class}">{score}/100</span>
                            </div>
                            <div class="job-company">{company}</div>
                            <div class="job-meta">
                                {location}
                                {f' | {salary_str}' if salary_str else ''}
                            </div>
                        </div>
        """

    def _build_text_body(
        self,
        run_number: int,
        new_jobs: list,
        top_jobs_overall: list,
        stats: dict,
        success: bool,
        error: Optional[str]
    ) -> str:
        """Build plain text email body."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            f"JOB SEARCH REPORT #{run_number}",
            f"Generated: {timestamp}",
            "=" * 60,
            "",
        ]

        if not success and error:
            lines.extend([
                "ERROR:",
                error,
                "",
            ])

        # New jobs (shown first)
        if new_jobs:
            lines.extend([
                "NEW JOBS FROM THIS RUN",
                "-" * 40,
            ])
            for i, job in enumerate(new_jobs[:10], 1):
                score = job.get('score', 0) or 0
                title = job.get('title', 'Unknown')
                company = job.get('company', 'Unknown')
                url = job.get('url', '')
                lines.extend([
                    f"{i}. [{score}/100] {title} @ {company}",
                    f"   {url}",
                    "",
                ])

        # Top jobs overall
        if top_jobs_overall:
            lines.extend([
                "TOP JOBS OVERALL",
                "-" * 40,
            ])
            for i, job in enumerate(top_jobs_overall[:10], 1):
                score = job.get('score', 0) or 0
                title = job.get('title', 'Unknown')
                company = job.get('company', 'Unknown')
                url = job.get('url', '')
                lines.extend([
                    f"{i}. [{score}/100] {title} @ {company}",
                    f"   {url}",
                    "",
                ])

        # Stats (at the end)
        prompt_tokens = stats.get('prompt_tokens', 0)
        completion_tokens = stats.get('completion_tokens', 0)
        est_cost = (prompt_tokens * 2 + completion_tokens * 8) / 1000000

        lines.extend([
            "RUN STATISTICS",
            "-" * 40,
            f"Jobs Found: {stats.get('jobs_found', 0)}",
            f"New Jobs: {stats.get('jobs_new', 0)}",
            f"Duration: {stats.get('duration_seconds', 0):.1f} seconds",
            f"API Calls: {stats.get('api_calls', 0)}",
            f"Prompt Tokens: {prompt_tokens:,}",
            f"Completion Tokens: {completion_tokens:,}",
            f"Est. Cost: ${est_cost:.4f}",
            "",
        ])

        lines.extend([
            "=" * 60,
            "Generated by Multi-Source Job Agent",
        ])

        return "\n".join(lines)


def create_email_reporter_from_config():
    """Create EmailReporter from environment configuration.

    Returns:
        EmailReporter instance if configured, None otherwise.
    """
    import os
    from dotenv import load_dotenv
    load_dotenv()

    # Check if email reporting is enabled
    if not os.getenv("EMAIL_ENABLED", "").lower() in ("true", "1", "yes"):
        logger.debug("Email reporting is disabled")
        return None

    # Required settings
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    sender_email = os.getenv("SMTP_SENDER_EMAIL")
    sender_password = os.getenv("SMTP_SENDER_PASSWORD")
    recipient_email = os.getenv("EMAIL_RECIPIENT")

    if not all([smtp_server, sender_email, sender_password, recipient_email]):
        logger.warning(
            "Email reporting enabled but not fully configured. "
            "Required: SMTP_SERVER, SMTP_SENDER_EMAIL, SMTP_SENDER_PASSWORD, EMAIL_RECIPIENT"
        )
        return None

    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

    return EmailReporter(
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        sender_email=sender_email,
        sender_password=sender_password,
        recipient_email=recipient_email,
        use_tls=use_tls
    )
