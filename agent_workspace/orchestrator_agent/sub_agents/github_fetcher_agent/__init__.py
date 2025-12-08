"""GitHub Fetcher Agent Package

Exports the GitHub fetcher agent for retrieving PR data.
"""

from .agent import github_fetcher_agent, create_github_fetcher_agent

__all__ = ['github_fetcher_agent', 'create_github_fetcher_agent']
