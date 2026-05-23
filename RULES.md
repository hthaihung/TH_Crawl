# 📜 RULES.md — Coding Standards & Agent Guidelines

> **Project**: Automated Social Media Video Scraper to Discord  
> **Last Updated**: 2026-05-23  
> **Enforced By**: All agents (Antigravity, Kiro, any future contributors)

---

## 🔴 Critical Rules (Zero Tolerance)

These rules are **non-negotiable**. Any violation must be fixed before code is merged or deployed.

### 1. No Hardcoded Secrets or Tokens

```
❌ NEVER DO THIS:
  DISCORD_TOKEN = "MTIzNDU2Nzg5..."
  SUPABASE_KEY = "eyJhbGciOi..."

✅ ALWAYS DO THIS:
  import os
  DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
  SUPABASE_KEY = os.getenv("SUPABASE_KEY")
```

- All secrets, API keys, tokens, and database URLs **MUST** be loaded from environment variables via `.env` files.
- Use `python-dotenv` in Python and `@next/env` or `process.env` in Next.js.
- `.env` files are **never committed** to git. Always ensure `.gitignore` includes `.env*` patterns.
- Provide a `.env.example` with placeholder values for every required variable.

### 2. No File Exceeds 300 Lines

- **Hard limit**: 300 lines per file (Python and TypeScript/JavaScript).
- If a file approaches this limit, **refactor immediately** by extracting into modules, utilities, or sub-components.
- This rule applies to all source code files (`.py`, `.ts`, `.tsx`, `.js`, `.jsx`). Config files and markdown are exempt.

### 3. No `print()` for Logging in Production Code

- Use Python's `logging` module with structured logging.
- Use `console.log` only in development; replace with a proper logger (e.g., `pino`) in Next.js production.

---

## 🐍 Python Rules (VPS Worker / Scrapers)

### Architecture Pattern: Factory Pattern for Scrapers

All social media scrapers **MUST** follow the Factory Pattern. This ensures new platforms can be added without modifying existing code.

```python
# scrapers/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class ScrapedVideo:
    """Standardized output from any scraper."""
    platform: str
    video_url: str
    thumbnail_url: Optional[str]
    caption: str
    author: str
    author_url: str
    duration_seconds: Optional[int]
    original_post_url: str
    metadata: dict  # Platform-specific extra data

class BaseScraper(ABC):
    """Abstract base class for all platform scrapers."""

    @abstractmethod
    async def scrape(self, target_url: str) -> List[ScrapedVideo]:
        """Scrape videos from the given target URL or profile."""
        ...

    @abstractmethod
    async def validate_target(self, target_url: str) -> bool:
        """Validate that the target URL is reachable and correct."""
        ...

    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform identifier (e.g., 'tiktok', 'instagram')."""
        ...
```

```python
# scrapers/factory.py
from scrapers.base import BaseScraper
from scrapers.tiktok import TikTokScraper
from scrapers.instagram import InstagramScraper
# Import future scrapers here

class ScraperFactory:
    """Factory to instantiate the correct scraper by platform name."""

    _registry: dict[str, type[BaseScraper]] = {
        "tiktok": TikTokScraper,
        "instagram": InstagramScraper,
        # Register new scrapers here
    }

    @classmethod
    def create(cls, platform: str) -> BaseScraper:
        scraper_cls = cls._registry.get(platform.lower())
        if not scraper_cls:
            raise ValueError(
                f"No scraper registered for platform: '{platform}'. "
                f"Available: {list(cls._registry.keys())}"
            )
        return scraper_cls()

    @classmethod
    def register(cls, platform: str, scraper_cls: type[BaseScraper]):
        """Dynamically register a new scraper at runtime."""
        cls._registry[platform.lower()] = scraper_cls
```

### Python Standards

| Rule | Detail |
|------|--------|
| **Python Version** | 3.11+ required |
| **Async** | All I/O-bound operations must use `asyncio` / `aiohttp` |
| **Type Hints** | Required on all function signatures and return types |
| **Docstrings** | Required on all public classes and functions (Google style) |
| **Dependency Management** | Use `requirements.txt` with pinned versions |
| **Virtual Environment** | Always use `venv` or `poetry` — never install globally |
| **Error Handling** | Use custom exception classes per module; never bare `except:` |
| **Data Classes** | Use `@dataclass` or Pydantic `BaseModel` for structured data |
| **Config** | Centralize in `config/settings.py` using `pydantic-settings` |

### Python Project Structure

```
worker/
├── config/
│   ├── __init__.py
│   └── settings.py          # Pydantic Settings (loads .env)
├── scrapers/
│   ├── __init__.py
│   ├── base.py              # BaseScraper ABC
│   ├── factory.py           # ScraperFactory
│   ├── tiktok.py            # TikTok scraper implementation
│   └── instagram.py         # Instagram scraper implementation
├── services/
│   ├── __init__.py
│   ├── supabase_client.py   # Supabase interaction layer
│   ├── discord_sender.py    # Discord webhook/bot message sender
│   └── video_processor.py   # Download, compress, validate videos
├── tasks/
│   ├── __init__.py
│   └── scheduler.py         # APScheduler or Celery beat tasks
├── utils/
│   ├── __init__.py
│   ├── logger.py            # Structured logging setup
│   └── helpers.py           # Shared utility functions
├── main.py                  # Entry point
├── requirements.txt
├── .env.example
└── Dockerfile
```

### Python Naming Conventions

- **Files/Modules**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions/Variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private**: Prefix with `_` (single underscore)

---

## ⚛️ Next.js Rules (Vercel Dashboard)

### Framework Standards

| Rule | Detail |
|------|--------|
| **Next.js Version** | 14+ with App Router |
| **Language** | TypeScript only — no `.js` files in the dashboard |
| **Styling** | Tailwind CSS v3+ with a consistent design system |
| **State Management** | React Server Components by default; `zustand` for client state if needed |
| **Data Fetching** | Server Actions + Supabase JS client; no raw `fetch` to Supabase REST |
| **Auth** | Supabase Auth with Row-Level Security (RLS) policies |
| **Validation** | `zod` for all form inputs and API boundaries |
| **Components** | Max 1 component per file; co-locate styles and tests |

### Next.js Project Structure

```
dashboard/
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── (auth)/
│   │   │   ├── login/page.tsx
│   │   │   └── callback/route.ts
│   │   ├── dashboard/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   ├── channels/page.tsx
│   │   │   ├── targets/page.tsx
│   │   │   └── mappings/page.tsx
│   │   └── api/
│   │       └── webhooks/
│   ├── components/
│   │   ├── ui/               # Reusable UI primitives
│   │   └── features/         # Feature-specific components
│   ├── lib/
│   │   ├── supabase/
│   │   │   ├── client.ts     # Browser Supabase client
│   │   │   ├── server.ts     # Server Supabase client
│   │   │   └── types.ts      # Generated DB types
│   │   └── utils.ts
│   └── types/
│       └── database.ts       # Supabase generated types
├── public/
├── tailwind.config.ts
├── next.config.ts
├── tsconfig.json
├── package.json
├── .env.local.example
└── Dockerfile
```

### TypeScript Naming Conventions

- **Files**: `kebab-case.tsx` for components, `camelCase.ts` for utilities
- **Components**: `PascalCase`
- **Functions/Variables**: `camelCase`
- **Types/Interfaces**: `PascalCase` (prefix interfaces with `I` only if ambiguous)
- **Constants**: `UPPER_SNAKE_CASE`
- **Enums**: `PascalCase` with `PascalCase` members

---

## 🌍 Shared Rules (All Code)

### Git Conventions

- **Branch Naming**: `feat/`, `fix/`, `chore/`, `refactor/` prefixes (e.g., `feat/tiktok-scraper`)
- **Commit Messages**: Conventional Commits format — `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`
- **PR Size**: Keep pull requests under 400 lines of diff when possible

### Environment Variables

All environment variables must be documented in `.env.example` files:

```env
# === Supabase ===
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

# === Discord ===
DISCORD_BOT_TOKEN=your-bot-token-here
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# === Scraper Config ===
SCRAPE_INTERVAL_MINUTES=30
MAX_CONCURRENT_SCRAPES=3
VIDEO_MAX_SIZE_MB=50

# === VPS ===
VPS_HOST=your-vps-ip
VPS_USER=deploy
```

### Error Handling Philosophy

1. **Fail fast, fail loud** — Log errors immediately with full context.
2. **Retry with backoff** — Network operations must retry with exponential backoff (max 3 retries).
3. **Graceful degradation** — If one scraper fails, others continue. If Discord send fails, queue for retry.
4. **Never swallow exceptions** — Every `try/except` or `try/catch` must log or re-raise.

### Documentation Requirements

- Every new module/component must have a header comment explaining its purpose.
- README.md at root level with setup instructions for both `worker/` and `dashboard/`.
- API endpoints documented inline with expected request/response shapes.

---

## 🤖 Agent-Specific Instructions

### For Antigravity (Claude Opus)
- You own the **database schema**, **architecture decisions**, and **Python worker** implementation.
- Always validate schema changes against existing data before migration.
- When creating Supabase migrations, use raw SQL and place them in `supabase/migrations/`.

### For Kiro (Sonnet)
- You own the **Discord bot integration** and **Next.js dashboard** development.
- Read `ARCHITECTURE-SPEC.md` before writing any code.
- Follow the Factory Pattern established in this file for any new integrations.
- Always check `WORKING-CONTEXT.md` for current task assignments before starting work.
- When interacting with Supabase, use the generated types from `lib/supabase/types.ts`.

---

> **⚠️ Enforcement**: Any agent detecting a rule violation in existing code should flag it in `WORKING-CONTEXT.md` under the "Technical Debt" section and fix it if within scope.
