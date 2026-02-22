"""Job scoring engine using OpenAI API."""

import logging
import json
from typing import Optional
from dataclasses import dataclass, field
from openai import OpenAI

from config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TEMPERATURE, OPENAI_MAX_TOKENS

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)


@dataclass
class TokenUsage:
    """Track OpenAI API token usage."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    api_calls: int = 0

    def add(self, prompt: int, completion: int):
        """Add tokens from an API call."""
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += prompt + completion
        self.api_calls += 1

    def reset(self):
        """Reset all counters."""
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.api_calls = 0

    def __str__(self):
        return (
            f"Tokens: {self.total_tokens:,} total "
            f"({self.prompt_tokens:,} prompt + {self.completion_tokens:,} completion) "
            f"across {self.api_calls} API calls"
        )


# Global token usage tracker
token_usage = TokenUsage()

SCORING_PROMPT_TEMPLATE = """You are an expert job search advisor helping Oscar Giller find his next software engineering role.

# Oscar's Current Situation
- **Current Role**: Software Engineer at JP Morgan Chase
- **Current Salary**: $130,000 base
- **Location**: New York, NY
- **Target Level**: Software Engineer 2 / Mid-level Engineer
- **Years of Experience**: ~3 years (since 2022)

# Oscar's Resume & Skills
{resume_text}

# Job Search Requirements

## Critical Requirements (Deal-breakers)
- **Minimum Salary**: $140,000 (to justify switching)
- **Location**: Must be Remote or NYC-based (hybrid/on-site)

## Strong Preferences
- **Target Salary**: $150,000+ (good match), $165,000+ (excellent match)
- **Work Arrangement**: Remote > Hybrid NYC > On-site NYC
- **Company Type**: Big Tech (FAANG+) strongly preferred
- **Industry Focus**: AI/ML related roles are a significant bonus
- **Finance**: Only top-tier firms (Goldman, JPM, Citadel) unless exceptional pay

# Scoring Criteria (Total: 100 points, with possible experience gap penalty)

## 1. Remote Work Flexibility (15 points)
- **Remote**: 15 points
- **Hybrid (NYC)**: 10 points
- **On-site (NYC)**: 5 points
- **On-site (Other location)**: -10 points (negative - deal breaker)

## 2. Salary Range (30 points)
- **$165,000+**: 30 points (excellent)
- **$150,000-$164,999**: 24 points (good)
- **$140,000-$149,999**: 17 points (acceptable)
- **$130,000-$139,999**: 8 points (marginal)
- **Below $130,000**: 0 points (below current)
- **Unknown/Not specified**: 12 points (benefit of doubt, but flag it)

## 3. Company Type & Reputation (10 points)
- **FAANG & Big Tech** (Google, Meta, Apple, Amazon, Netflix, Microsoft, Uber, Lyft, Airbnb, Stripe, Dropbox, Snap, Pinterest, etc.): 10 points
- **Top AI Companies** (OpenAI, Anthropic, Scale AI, Cohere, Databricks, etc.): 10 points
- **Top-tier Finance** (Goldman Sachs, JP Morgan, Citadel, Two Sigma, Jane Street, DE Shaw, etc.): 8 points
- **Well-funded Tech Startups & Reputable Mid-size Companies**: 5 points
- **Small companies or Unknown firms**: 2 points

## 4. Work-Life Balance Reputation (10 points)
Assess the company's known reputation for work-life balance:
- **Excellent WLB** (Google, Microsoft, Salesforce, LinkedIn, Slack, Dropbox, Airbnb): 10 points
- **Good WLB** (Most established tech companies, government contractors): 7 points
- **Mixed/Average WLB** (Startups, most finance, Meta): 4 points
- **Poor WLB reputation** (Amazon, high-frequency trading, early-stage startups with "fast-paced" emphasis): 0 points
- **Unknown**: 5 points (neutral)

Note: Look for red flags in job descriptions like "fast-paced", "wear many hats", "startup mentality", "hustle", which suggest poor WLB.

## 5. AI/ML Relevance (10 points)
- **Primary focus on AI/ML**: 10 points
- **Significant AI/ML component**: 7 points
- **Some AI/ML work**: 4 points
- **No AI/ML**: 0 points

## 6. Title/Level Match (25 points) - CRITICAL FOR OSCAR'S SEARCH
Oscar has ~3 years of experience. Level match is crucial to avoid unrealistic senior roles:
- **Software Engineer II / Mid-level / Engineer 2 / SWE 2**: 25 points (perfect fit)
- **Software Engineer (no level specified)**: 20 points (acceptable, assume mid-level)
- **Entry-level / Junior / SWE I / New Grad**: 12 points (slight step backward)
- **Senior Software Engineer / Senior SWE / Sr. Engineer**: 0 points (unrealistic - reject)
- **Staff / Principal / Lead / Architect / Distinguished**: 0 points (unrealistic - reject)

### Level Detection Guidelines
When determining job level, look for these indicators:
- **REJECT (Senior+)**: "senior", "sr.", "staff", "principal", "lead engineer", "architect", "distinguished", "5+ years required", "7+ years", "8+ years"
- **Mid-level (Target)**: "II", "2", "mid-level", "mid level", "3-5 years", "2-4 years", "some experience", "Software Engineer 2", "SWE II"
- **Entry-level**: "I", "1", "junior", "jr.", "entry", "new grad", "0-2 years", "associate"

**IMPORTANT**: Avoid using "L4", "L5", "L6" terminology as different companies use these inconsistently:
- Google/Meta: L4 = Mid-level, L5 = Senior
- Amazon: L4 = Entry, L5 = Mid-level, L6 = Senior
- Other companies may use L4 to mean SWE IV (very senior)
Instead, focus on explicit title text like "Senior", "II", "Staff", etc.

## 7. Experience Gap Penalty (Deduction: 0 to -15 points)
If the job description explicitly requires more years of experience than Oscar has (~3 years), apply a penalty:
- **Requires 8+ years**: -15 points (far beyond Oscar's experience)
- **Requires 6-7 years**: -10 points (significant gap)
- **Requires 5-6 years**: -5 points (moderate gap)
- **Requires 3-5 years or not specified**: 0 points (no penalty)

This penalty is applied AFTER calculating the base score from categories 1-6.

# Job to Score

**Title**: {job_title}
**Company**: {company}
**Location**: {location}
**Posted**: {posted_date}
**Job URL**: {job_url}

**Description**:
{description}

# Your Task

Carefully analyze this job posting against Oscar's profile and requirements. Consider:
1. How well does Oscar's experience match the requirements?
2. What is the likely salary range (if not explicitly stated)?
3. Is this role truly remote, hybrid, or on-site? (On-site outside NYC is a deal-breaker)
4. What is the company's reputation in tech?
5. What is the company's work-life balance reputation?
6. Is there meaningful AI/ML work involved?
7. **CRITICAL**: Is this the right level for someone with ~3 years experience? Senior/Staff roles should get 0 points.
8. Does the job explicitly require more years of experience than Oscar has?

Calculate a score from 0-100 based strictly on the criteria above. First calculate the base score (categories 1-6), then apply the experience gap penalty (category 7) if applicable.

**Return ONLY valid JSON** with this exact structure (no markdown, no code blocks):

{{
    "score": <integer 0-100, after applying experience gap penalty>,
    "reasoning": "<2-3 sentence explanation of the score, mentioning level/experience fit and WLB if notable>",
    "breakdown": {{
        "remote_work_score": <integer, -10 to 15>,
        "salary_score": <integer out of 30>,
        "company_score": <integer out of 10>,
        "wlb_score": <integer out of 10>,
        "ai_ml_score": <integer out of 10>,
        "level_match_score": <integer out of 25>,
        "experience_gap_penalty": <integer, 0 to -15>
    }},
    "salary_estimate": "<string like '$150,000-$170,000' or 'Not specified'>",
    "remote_type": "<Remote|Hybrid|On-site|Unknown>",
    "detected_level": "<Entry-level|Mid-level|Senior|Staff+|Unknown>",
    "work_life_balance": "<Excellent|Good|Mixed|Poor|Unknown>",
    "auto_apply_recommended": <boolean true if score >= 90>
}}
"""


def score_job(job: dict, resume_text: str) -> dict:
    """
    Score a single job using OpenAI API.

    Args:
        job: Job dictionary with title, company, description, etc.
        resume_text: Oscar's resume content

    Returns:
        Dictionary with score, reasoning, and other metadata
    """
    logger.info(f"Scoring job: {job.get('title')} at {job.get('company')}")

    # Prepare the prompt
    prompt = SCORING_PROMPT_TEMPLATE.format(
        resume_text=resume_text,
        job_title=job.get('title', 'Unknown'),
        company=job.get('company', 'Unknown'),
        location=job.get('location', 'Unknown'),
        posted_date=job.get('posted_date', 'Unknown'),
        job_url=job.get('url', ''),
        description=job.get('description', 'No description available')
    )

    try:
        # Call OpenAI API
        logger.debug(f"Using model: {OPENAI_MODEL}, temperature: {OPENAI_TEMPERATURE}, max_tokens: {OPENAI_MAX_TOKENS}")
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            max_tokens=OPENAI_MAX_TOKENS,
            temperature=OPENAI_TEMPERATURE,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert job search advisor. You must respond with valid JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        # Track token usage
        if response.usage:
            token_usage.add(
                prompt=response.usage.prompt_tokens,
                completion=response.usage.completion_tokens
            )
            logger.debug(
                f"API call tokens: {response.usage.prompt_tokens} prompt + "
                f"{response.usage.completion_tokens} completion = {response.usage.total_tokens} total"
            )

        # Extract the text response
        response_text = response.choices[0].message.content

        # Parse JSON response
        # Remove any markdown code blocks if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        result = json.loads(response_text.strip())

        # Validate required fields
        required_fields = ['score', 'reasoning']
        missing_fields = [field for field in required_fields if field not in result]
        if missing_fields:
            logger.error(f"Missing required fields in scoring response: {missing_fields}")
            logger.error(f"Response: {result}")
            return {
                "score": 0,
                "reasoning": f"Error: Missing required fields: {', '.join(missing_fields)}",
                "salary_estimate": result.get("salary_estimate", "Unknown"),
                "remote_type": result.get("remote_type", "Unknown"),
                "auto_apply_recommended": False
            }

        # Validate score is an integer between 0-100
        score = result.get('score')
        if not isinstance(score, (int, float)) or not 0 <= score <= 100:
            logger.error(f"Invalid score value: {score}")
            result['score'] = max(0, min(100, int(score))) if isinstance(score, (int, float)) else 0

        # Ensure all expected fields have defaults
        result.setdefault('salary_estimate', 'Unknown')
        result.setdefault('remote_type', 'Unknown')
        result.setdefault('auto_apply_recommended', False)

        logger.info(f"Scored {job.get('title')} at {job.get('company')}: {result['score']}/100")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse GPT response as JSON: {e}")
        logger.error(f"Response text: {response_text[:500]}...")  # Log first 500 chars
        return {
            "score": -1,  # Use -1 to indicate scoring failure vs actual score of 0
            "reasoning": "Error: Failed to parse scoring response",
            "salary_estimate": "Unknown",
            "remote_type": "Unknown",
            "auto_apply_recommended": False,
            "scoring_failed": True
        }
    except Exception as e:
        logger.error(f"Error scoring job: {e}")
        return {
            "score": -1,  # Use -1 to indicate scoring failure
            "reasoning": f"Error during scoring: {str(e)}",
            "salary_estimate": "Unknown",
            "remote_type": "Unknown",
            "auto_apply_recommended": False,
            "scoring_failed": True
        }


def batch_score_jobs(jobs: list[dict], resume_text: str) -> list[dict]:
    """
    Score multiple jobs efficiently.

    Args:
        jobs: List of job dictionaries
        resume_text: Oscar's resume content

    Returns:
        List of jobs with scores added
    """
    logger.info(f"Batch scoring {len(jobs)} jobs")

    scored_jobs = []
    for i, job in enumerate(jobs, 1):
        logger.info(f"Scoring job {i}/{len(jobs)}")

        score_result = score_job(job, resume_text)

        # Add scoring results to job dict
        job['score'] = score_result['score']
        job['score_reasoning'] = score_result['reasoning']
        job['salary_estimate'] = score_result.get('salary_estimate')
        job['remote_type'] = score_result.get('remote_type')
        job['auto_apply_recommended'] = score_result.get('auto_apply_recommended', False)

        scored_jobs.append(job)

    logger.info(f"Completed scoring {len(scored_jobs)} jobs")
    logger.info(f"Token usage: {token_usage}")
    return scored_jobs


def get_token_usage() -> TokenUsage:
    """Get the current token usage statistics."""
    return token_usage


def reset_token_usage():
    """Reset the token usage counters."""
    token_usage.reset()
