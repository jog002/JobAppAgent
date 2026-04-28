"""Curated registry of companies and their ATS job board URLs.

This registry contains companies across different categories:
- AI/ML companies
- Big tech with public ATS boards
- Y Combinator companies
- Remote-first companies

Users can customize this list by editing this file directly.
"""

COMPANY_REGISTRY = [
    # ===== AI/ML Companies =====
    {'name': 'Anthropic', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/anthropic'},
    {'name': 'OpenAI', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/openai'},
    {'name': 'Cohere', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/cohere'},
    {'name': 'HuggingFace', 'ats': 'lever', 'url': 'https://jobs.lever.co/huggingface'},
    {'name': 'Stability AI', 'ats': 'lever', 'url': 'https://jobs.lever.co/stabilityai'},
    {'name': 'Scale AI', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/scaleai'},
    {'name': 'Runway', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/runwayml'},
    {'name': 'Character.AI', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/characterai'},
    {'name': 'Inflection AI', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/inflection'},
    {'name': 'Adept', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/adept'},
    {'name': 'AI21 Labs', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/ai21labs'},
    {'name': 'Replicate', 'ats': 'lever', 'url': 'https://jobs.lever.co/replicate'},
    {'name': 'Weights & Biases', 'ats': 'lever', 'url': 'https://jobs.lever.co/wandb'},
    {'name': 'Midjourney', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/midjourney'},

    # ===== Big Tech & Unicorns with Public ATS =====
    {'name': 'Stripe', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/stripe'},
    {'name': 'Shopify', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/shopify'},
    {'name': 'Databricks', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/databricks'},
    {'name': 'Snowflake', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/snowflake'},
    {'name': 'Coinbase', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/coinbase'},
    {'name': 'Notion', 'ats': 'lever', 'url': 'https://jobs.lever.co/notion'},
    {'name': 'Figma', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/figma'},
    {'name': 'Canva', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/canva'},
    {'name': 'Airtable', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/airtable'},
    {'name': 'Linear', 'ats': 'ashby', 'url': 'https://jobs.ashbyhq.com/linear'},
    {'name': 'Vercel', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/vercel'},
    {'name': 'Plaid', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/plaid'},
    {'name': 'Brex', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/brex'},
    {'name': 'Ramp', 'ats': 'ashby', 'url': 'https://jobs.ashbyhq.com/ramp'},
    {'name': 'Rippling', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/rippling'},

    # ===== Y Combinator Companies =====
    {'name': 'Retool', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/retool'},
    {'name': 'Lattice', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/lattice'},
    {'name': 'Flexport', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/flexport'},
    {'name': 'Gusto', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/gusto'},
    {'name': 'GitLab', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/gitlab'},
    {'name': 'Instacart', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/instacart'},
    {'name': 'Zapier', 'ats': 'lever', 'url': 'https://jobs.lever.co/zapier'},
    {'name': 'Webflow', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/webflow'},
    {'name': 'Checkr', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/checkr'},

    # ===== Remote-First Companies =====
    {'name': 'Automattic', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/automattic'},
    {'name': 'Buffer', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/buffer'},
    {'name': 'Doist', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/doist'},
    {'name': 'Toptal', 'ats': 'lever', 'url': 'https://jobs.lever.co/toptal'},
    {'name': 'Remote', 'ats': 'lever', 'url': 'https://jobs.lever.co/remote'},
    {'name': 'Elastic', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/elastic'},
    {'name': 'HashiCorp', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/hashicorp'},

    # ===== Additional High-Growth Companies =====
    {'name': 'Anduril', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/anduril'},
    {'name': 'Navan', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/navan'},
    {'name': 'Faire', 'ats': 'greenhouse', 'url': 'https://boards.greenhouse.io/faire'},
    {'name': 'Census', 'ats': 'ashby', 'url': 'https://jobs.ashbyhq.com/census'},
    {'name': 'Monte Carlo', 'ats': 'lever', 'url': 'https://jobs.lever.co/montecarlodata'},
    {'name': 'Weights & Biases', 'ats': 'lever', 'url': 'https://jobs.lever.co/wandb'},
    {'name': 'Modal', 'ats': 'ashby', 'url': 'https://jobs.ashbyhq.com/modal'},
]


def load_company_registry(custom_path=None):
    """
    Load company registry from default list or custom file.

    Args:
        custom_path: Optional path to custom company registry JSON file

    Returns:
        List of company dictionaries with 'name', 'ats', and 'url' fields
    """
    if custom_path:
        import json
        import logging
        logger = logging.getLogger(__name__)

        try:
            with open(custom_path, 'r') as f:
                custom_registry = json.load(f)
            logger.info(f"Loaded {len(custom_registry)} companies from custom registry: {custom_path}")
            return custom_registry
        except Exception as e:
            logger.error(f"Failed to load custom registry from {custom_path}: {e}")
            logger.info("Falling back to default company registry")

    return COMPANY_REGISTRY
