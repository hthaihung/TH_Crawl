# 🎬 CrawlStory

Automated Social Media Video Scraper to Discord — Intelligently routes videos from TikTok, Instagram, YouTube Shorts, and Twitter to Discord channels using AI-suggested mappings.

---

## 📋 Project Status

**Current Phase**: Automated Media Delivery Complete  
**Last Updated**: 2026-05-23

| Component | Status |
|-----------|--------|
| Python Worker Environment | ✅ Complete |
| Database Schema | ✅ Complete |
| Discord Bot | ✅ Complete |
| Channel Synchronization | ✅ Complete |
| Scraper Architecture | ✅ Complete |
| TikTok Scraper | ✅ Complete |
| Media Orchestrator | ✅ Complete |
| Automated Delivery Loop | ✅ Complete |
| Next.js Dashboard | ⏳ Pending |

---

## 🚀 Quick Start

**📖 For detailed setup instructions, see [SETUP-GUIDE.md](SETUP-GUIDE.md)**

### Prerequisites

- Python 3.11+
- Node.js 18+ (for dashboard)
- Supabase account
- Discord bot token

### Quick Setup

```bash
# 1. Install dependencies
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 3. Run the bot
python src/main.py
```

The bot will automatically sync all Discord channels to Supabase on startup.

---

## 📁 Project Structure

```
CrawlStory/
├── src/
│   ├── __init__.py
│   ├── main.py                    # Entry point
│   ├── database/
│   │   ├── __init__.py
│   │   └── supabase_client.py     # ✅ Supabase client singleton
│   ├── bot/
│   │   ├── __init__.py
│   │   └── core.py                # ✅ Discord bot with channel sync
│   └── scrapers/
│       ├── __init__.py            # ✅ Module exports & auto-registration
│       ├── base.py                # ✅ BaseScraper & ScrapedVideo
│       ├── factory.py             # ✅ ScraperFactory
│       └── tiktok.py              # ✅ TikTok scraper
├── requirements.txt               # ✅ Python dependencies
├── .env.example                   # ✅ Environment template
├── RULES.md                       # 📜 Coding standards
├── ARCHITECTURE-SPEC.md           # 🏛️ System architecture
├── WORKING-CONTEXT.md             # 📋 Task tracking
└── README.md                      # 📖 This file
```

---

## 🏗️ Architecture Overview

```
┌─────────────────┐      ┌──────────────┐      ┌─────────────┐
│  Next.js        │◄────►│  Supabase    │◄────►│  Python     │
│  Dashboard      │      │  PostgreSQL  │      │  Worker     │
│  (Vercel)       │      │  + Auth      │      │  (VPS)      │
└─────────────────┘      └──────────────┘      └─────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │  Discord API    │
                                              │  (Webhooks/Bot) │
                                              └─────────────────┘
```

### Core Components

1. **Python Worker (VPS)**: Scrapes social media, processes videos, sends to Discord
2. **Supabase**: Central database, authentication, and file storage
3. **Next.js Dashboard (Vercel)**: Web UI for managing channels, targets, and AI mappings
4. **Discord Integration**: Delivers videos via webhooks or bot

---

## 📚 Documentation

- **[SETUP-GUIDE.md](SETUP-GUIDE.md)**: Complete step-by-step setup instructions
- **[SCRAPER-GUIDE.md](SCRAPER-GUIDE.md)**: Scraper architecture and how to add new platforms
- **[RULES.md](RULES.md)**: Coding standards, naming conventions, and agent guidelines
- **[ARCHITECTURE-SPEC.md](ARCHITECTURE-SPEC.md)**: Detailed system architecture and database schema
- **[WORKING-CONTEXT.md](WORKING-CONTEXT.md)**: Current task status and project tracking

---

## 🔐 Security Notes

- **Never commit `.env` files** — they contain sensitive credentials
- Use `.env.example` as a template for required variables
- The worker uses `SUPABASE_SERVICE_ROLE_KEY` to bypass Row-Level Security (RLS)
- The dashboard uses `SUPABASE_ANON_KEY` with RLS enforced

---

## 🛠️ Development Workflow

### Adding a New Social Media Platform

1. Create a new scraper class in `src/scrapers/` inheriting from `BaseScraper`
2. Implement required methods: `scrape()`, `validate_target()`, `platform_name()`
3. Register the scraper in `ScraperFactory._registry`
4. Add platform to the `social_targets.platform` CHECK constraint in the database

### Running Tests

```bash
# Tests will be added in future iterations
pytest tests/
```

---

## 📝 Current Tasks

See [WORKING-CONTEXT.md](WORKING-CONTEXT.md) for the complete task list and status.

**Next Steps**:
1. ✅ Environment setup (K-0) — **COMPLETED**
2. ✅ Discord bot integration (K-1) — **COMPLETED**
3. ✅ Core scraper architecture (A-6) — **COMPLETED**
4. ✅ Media orchestrator & delivery (K-2) — **COMPLETED**
5. ⏳ Bot slash commands (K-3) — **PENDING**
6. ⏳ Supabase migration files (A-2) — **PENDING**

---

## 🤝 Contributing

This project follows strict coding standards defined in [RULES.md](RULES.md):

- **No file exceeds 300 lines**
- **No hardcoded secrets** — use environment variables
- **Type hints required** on all function signatures
- **Factory Pattern** for all scrapers

---

## 📄 License

_License to be determined_

---

## 🙏 Acknowledgments

Built with:
- [discord.py](https://github.com/Rapptz/discord.py) — Discord API wrapper
- [Supabase](https://supabase.com) — Backend-as-a-Service
- [Next.js](https://nextjs.org) — React framework for the dashboard

---

**Questions?** Check the documentation files or review the architecture spec.
