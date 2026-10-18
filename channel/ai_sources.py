"""Official update pages for popular AI assistants (LogicScript "What's new in <AI>" videos).

Only first-party pages: release notes, product blogs and newsrooms of the company that makes the
assistant. Every fact in a video must be quoted from one of these pages (see scripts/whats_new_plan.py),
and the video shows the real page while the narration talks about it. No mock-ups of the apps.
"""
from __future__ import annotations

AI_SOURCES: dict[str, dict] = {
    'claude': {
        'name': 'Claude', 'company': 'Anthropic',
        'pages': ['https://support.claude.com/en/articles/12138966-release-notes',
                  'https://www.anthropic.com/news',
                  'https://claude.com/blog'],
    },
    'chatgpt': {
        'name': 'ChatGPT', 'company': 'OpenAI',
        'pages': ['https://help.openai.com/en/articles/6825453-chatgpt-release-notes',
                  'https://openai.com/news/'],
    },
    'gemini': {
        'name': 'Gemini', 'company': 'Google',
        'pages': ['https://gemini.google/release-notes/',
                  'https://blog.google/products/gemini/'],
    },
    'copilot': {
        'name': 'Microsoft Copilot', 'company': 'Microsoft',
        'pages': ['https://www.microsoft.com/en-us/microsoft-copilot/blog/',
                  'https://learn.microsoft.com/en-us/copilot/microsoft-365/release-notes'],
    },
    'grok': {
        'name': 'Grok', 'company': 'xAI',
        'pages': ['https://x.ai/news'],
    },
    'perplexity': {
        'name': 'Perplexity', 'company': 'Perplexity',
        'pages': ['https://www.perplexity.ai/changelog'],
    },
    'meta-ai': {
        'name': 'Meta AI', 'company': 'Meta',
        'pages': ['https://about.fb.com/news/tag/meta-ai/'],
    },
    'deepseek': {
        'name': 'DeepSeek', 'company': 'DeepSeek',
        'pages': ['https://api-docs.deepseek.com/news/news'],
    },
}


def official_hosts(ai: str) -> set[str]:
    from urllib.parse import urlparse
    return {urlparse(u).hostname for u in AI_SOURCES[ai]['pages']}
