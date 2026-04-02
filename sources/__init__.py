"""Job source abstraction layer."""
from typing import Dict, Type, List
from .base_source import BaseJobSource

# Source registry
_SOURCES: Dict[str, Type[BaseJobSource]] = {}
_SOURCES_LOADED = False


def _load_sources():
    """Load all source modules to trigger registration."""
    global _SOURCES_LOADED
    if _SOURCES_LOADED:
        return

    import logging
    logger = logging.getLogger(__name__)

    try:
        from .linkedin import linkedin_source
        logger.debug("LinkedIn source loaded")
    except Exception as e:
        logger.debug(f"LinkedIn source not available: {e}")

    try:
        from .web_scraping import web_scraping_source
        logger.debug("Web scraping source loaded")
    except Exception as e:
        logger.debug(f"Web scraping source not available: {e}")

    _SOURCES_LOADED = True


def register_source(name: str):
    """Decorator to register a job source."""
    def decorator(cls: Type[BaseJobSource]):
        _SOURCES[name] = cls
        return cls
    return decorator


def get_source(name: str, *args, **kwargs) -> BaseJobSource:
    """Get a job source by name."""
    if name not in _SOURCES:
        raise ValueError(f"Unknown source: {name}. Available sources: {list(_SOURCES.keys())}")
    return _SOURCES[name](*args, **kwargs)


def get_all_sources() -> List[str]:
    """Get all registered source names."""
    return list(_SOURCES.keys())


def get_enabled_sources(config) -> List[BaseJobSource]:
    """Get all enabled sources from config."""
    import logging
    logger = logging.getLogger(__name__)

    # Ensure sources are loaded
    _load_sources()

    enabled = config.ENABLED_SOURCES
    sources = []

    for name in enabled:
        name = name.strip()
        if not name:
            continue

        if name not in _SOURCES:
            logger.warning(f"Source '{name}' is enabled in config but not registered. Skipping.")
            continue

        try:
            # Create source instance with appropriate parameters
            if name == 'web_scraping':
                source = get_source(
                    name,
                    enabled_platforms=config.WEB_SCRAPING_PLATFORMS,
                    enabled_discovery_providers=getattr(config, 'ENABLED_DISCOVERY_PROVIDERS', None),
                    scraping_delay=config.SCRAPING_DELAY_SECONDS,
                    location_filter=getattr(config, 'LOCATION_TERMS', None),
                    jobspy_sites=getattr(config, 'JOBSPY_SITES', None),
                    jobspy_hours_old=getattr(config, 'JOBSPY_HOURS_OLD', 72),
                    search_mode=getattr(config, 'SEARCH_MODE', 'combined'),
                    level_terms=getattr(config, 'LEVEL_TERMS', None),
                    exclude_terms=getattr(config, 'EXCLUDE_LEVELS', None),
                )
            else:
                source = get_source(name)
            sources.append(source)
        except Exception as e:
            logger.error(f"Failed to initialize source '{name}': {e}")

    return sources
