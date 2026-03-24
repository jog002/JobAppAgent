"""Job scoring engine using LLM API (supports Claude and OpenAI)."""

import logging
import json
from typing import Optional
from dataclasses import dataclass

from config import (
    LLM_PROVIDER,
    CLAUDE_API_KEY, CLAUDE_MODEL, CLAUDE_TEMPERATURE, CLAUDE_MAX_TOKENS,
    OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TEMPERATURE, OPENAI_MAX_TOKENS
)

logger = logging.getLogger(__name__)

# Initialize the appropriate client based on provider
if LLM_PROVIDER == "claude":
    import anthropic
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
else:
    from openai import OpenAI
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

SCORING_PROMPT_TEMPLATE = """<role>
You are a job-fit scoring algorithm. Score job postings 0-100 for Oscar Giller against his profile. Be precise and consistent. Prioritize level-matching and ML-fit distinction above other criteria.
</role>

<critical_rules>
1. LEVEL IS MOST IMPORTANT: Senior/Staff/5+ years required roles get level_match_score = 0
2. LOCATION: Accept only Remote, NYC Hybrid, or NYC On-site. Other locations = dealbreaker (-10 points)
3. ML DISTINCTION: Oscar builds AI-POWERED APPLICATIONS (LLM APIs, RAG, agents). He is NOT an ML Engineer.
   - AI Application roles (working WITH AI/LLM APIs, building AI features): GOOD FIT
   - ML Engineer roles (training models, ML research, PhD required): POOR FIT, set ai_ml_score = 0
</critical_rules>

<candidate>
Oscar Giller | SWE II @ JP Morgan Chase | NYC | ~3 years experience (since 2022)
Current salary: $130K | Target: $150K+ | Minimum: $140K
Skills: Azure OpenAI, RAG systems, AI agents, React, TypeScript, Python, AWS, Terraform
Preferences: Remote > Hybrid NYC > On-site NYC | Big Tech/Top AI companies preferred

{resume_text}
</candidate>

<scoring total="100">
<remote points="15">Remote=15 | NYC Hybrid=10 | NYC On-site=5 | Other location=-10</remote>
<salary points="30">$165K+=30 | $150-164K=24 | $140-149K=17 | $130-139K=8 | Below $130K=0 | Unknown=12</salary>
<company points="10">FAANG/Big Tech/Top AI=10 | Top Finance=8 | Funded Startup=5 | Unknown=2</company>
<wlb points="10">Excellent=10 | Good=7 | Mixed=4 | Poor=0 | Unknown=5. Red flags: "fast-paced", "wear many hats", "hustle"</wlb>
<ai_ml points="10">
  AI App Engineering (APIs, RAG, agents, AI features)=10 | AI Platform/MLOps=8 | Some AI work=5 | No AI=0
  Pure ML Engineering (model training, ML research, PhD required)=0 and flag as mismatch
</ai_ml>
<level points="25">Mid-level/SWE II/2-4 yrs=25 | Unspecified=20 | Junior/Entry=12 | Senior/Staff+=0. Focus on explicit titles, ignore L4/L5/L6 numbering.</level>
<experience_penalty>8+ yrs required=-15 | 6-7 yrs=-10 | 5-6 yrs=-5 | 3-5 yrs or unspecified=0</experience_penalty>
</scoring>

<examples>
<example type="high_score">
<job>Title: Software Engineer II - AI Platform | Company: Anthropic | Location: Remote | Description: Build production systems powering Claude. Work with LLM APIs, develop AI agents, optimize inference pipelines. 3-5 years experience. $170K-$200K.</job>
<result>{{"score": 87, "reasoning": "Perfect level match (SWE II, 3-5 years). Top AI company, fully remote, excellent salary. AI application engineering aligns with Oscar's RAG/agent experience.", "breakdown": {{"remote_work_score": 15, "salary_score": 30, "company_score": 10, "wlb_score": 7, "ai_ml_score": 10, "level_match_score": 25, "experience_gap_penalty": -10}}, "salary_estimate": "$170,000-$200,000", "remote_type": "Remote", "detected_level": "Mid-level", "work_life_balance": "Good", "auto_apply_recommended": false}}</result>
</example>

<example type="ml_mismatch">
<job>Title: Machine Learning Engineer | Company: DeepMind | Location: London (On-site) | Description: Design and train novel neural architectures. PhD in ML required. Publish research at top venues. Deep expertise in PyTorch internals, gradient optimization, 5+ years.</job>
<result>{{"score": 12, "reasoning": "Wrong role type - ML research requiring PhD and model training, not AI application development. On-site London is a dealbreaker. Despite prestigious company, Oscar lacks ML theory background.", "breakdown": {{"remote_work_score": -10, "salary_score": 12, "company_score": 10, "wlb_score": 4, "ai_ml_score": 0, "level_match_score": 0, "experience_gap_penalty": -5}}, "salary_estimate": "Not specified", "remote_type": "On-site", "detected_level": "Senior", "work_life_balance": "Mixed", "auto_apply_recommended": false}}</result>
</example>

<example type="medium_score">
<job>Title: Software Engineer | Company: Stripe | Location: NYC (Hybrid) | Description: Build payment infrastructure. Python, distributed systems. 2-4 years experience.</job>
<result>{{"score": 59, "reasoning": "Good company and appropriate level. Hybrid NYC is acceptable. No AI/ML component reduces score. Salary likely competitive but unspecified.", "breakdown": {{"remote_work_score": 10, "salary_score": 12, "company_score": 10, "wlb_score": 7, "ai_ml_score": 0, "level_match_score": 20, "experience_gap_penalty": 0}}, "salary_estimate": "Not specified", "remote_type": "Hybrid", "detected_level": "Mid-level", "work_life_balance": "Good", "auto_apply_recommended": false}}</result>
</example>
</examples>

<job_to_score>
Title: {job_title}
Company: {company}
Location: {location}
Posted: {posted_date}
URL: {job_url}

Description:
{description}
</job_to_score>

<output_format>
Return ONLY valid JSON (no markdown, no code blocks):
{{
    "score": <integer 0-100>,
    "reasoning": "<2-3 sentences: level fit, ML fit if relevant, key factors>",
    "breakdown": {{
        "remote_work_score": <-10 to 15>,
        "salary_score": <0 to 30>,
        "company_score": <0 to 10>,
        "wlb_score": <0 to 10>,
        "ai_ml_score": <0 to 10>,
        "level_match_score": <0 to 25>,
        "experience_gap_penalty": <-15 to 0>
    }},
    "salary_estimate": "<range or 'Not specified'>",
    "remote_type": "<Remote|Hybrid|On-site|Unknown>",
    "detected_level": "<Entry-level|Mid-level|Senior|Staff+|Unknown>",
    "work_life_balance": "<Excellent|Good|Mixed|Poor|Unknown>",
    "auto_apply_recommended": <true if score >= 90>
}}
</output_format>
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
        # Call LLM API based on provider
        if LLM_PROVIDER == "claude":
            logger.debug(f"Using Claude model: {CLAUDE_MODEL}, temperature: {CLAUDE_TEMPERATURE}, max_tokens: {CLAUDE_MAX_TOKENS}")
            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=CLAUDE_MAX_TOKENS,
                temperature=CLAUDE_TEMPERATURE,
                system="You are an expert job search advisor. You must respond with valid JSON only.",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Track token usage (Claude uses input_tokens/output_tokens)
            if response.usage:
                token_usage.add(
                    prompt=response.usage.input_tokens,
                    completion=response.usage.output_tokens
                )
                logger.debug(
                    f"API call tokens: {response.usage.input_tokens} prompt + "
                    f"{response.usage.output_tokens} completion"
                )

            # Extract the text response
            response_text = response.content[0].text
        else:
            # OpenAI
            logger.debug(f"Using OpenAI model: {OPENAI_MODEL}, temperature: {OPENAI_TEMPERATURE}, max_tokens: {OPENAI_MAX_TOKENS}")
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

            # Track token usage (OpenAI uses prompt_tokens/completion_tokens)
            if response.usage:
                token_usage.add(
                    prompt=response.usage.prompt_tokens,
                    completion=response.usage.completion_tokens
                )
                logger.debug(
                    f"API call tokens: {response.usage.prompt_tokens} prompt + "
                    f"{response.usage.completion_tokens} completion"
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
