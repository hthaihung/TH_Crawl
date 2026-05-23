# 🚀 CrawlStory Setup Guide

Complete step-by-step guide to set up and run the CrawlStory Discord bot with automated channel synchronization.

---

## 📋 Prerequisites

Before you begin, ensure you have:

- **Python 3.11+** installed
- **Supabase account** (free tier is sufficient)
- **Discord bot** created and invited to your server
- **Discord Developer Mode** enabled (for copying IDs)

---

## 1️⃣ Supabase Setup

### Create a Supabase Project

1. Go to [https://app.supabase.com](https://app.supabase.com)
2. Click "New Project"
3. Fill in project details and wait for provisioning

### Run the Database Migration

1. In your Supabase project, go to **SQL Editor**
2. Copy the SQL migration from `ARCHITECTURE-SPEC.md` (section 4)
3. Paste and execute the migration to create all tables
4. Verify tables exist: `discord_channels`, `social_targets`, `ai_mappings`, `processed_videos`

### Get Your Credentials

1. Go to **Project Settings** → **API**
2. Copy the following values:
   - **Project URL** (e.g., `https://xxxxx.supabase.co`)
   - **anon public** key (for dashboard - future use)
   - **service_role** key (⚠️ **SECRET** - for worker only)

---

## 2️⃣ Discord Bot Setup

### Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **New Application**
3. Give it a name (e.g., "CrawlStory Bot")
4. Go to **Bot** section
5. Click **Add Bot**
6. Copy the **Bot Token** (⚠️ **SECRET** - keep this safe!)

### Configure Bot Permissions

1. In the **Bot** section, enable these **Privileged Gateway Intents**:
   - ✅ **Server Members Intent** (optional, for future features)
   - ✅ **Message Content Intent** (optional, for future commands)
2. In **OAuth2** → **URL Generator**:
   - Select scopes: `bot`, `applications.commands`
   - Select permissions:
     - ✅ View Channels
     - ✅ Send Messages
     - ✅ Embed Links
     - ✅ Attach Files
     - ✅ Read Message History
3. Copy the generated URL and open it in your browser
4. Select your Discord server and authorize the bot

### Get Your Guild ID

1. Open Discord
2. Enable **Developer Mode**: User Settings → Advanced → Developer Mode
3. Right-click on your server icon
4. Click **Copy ID** — this is your `DISCORD_GUILD_ID`

---

## 3️⃣ Project Setup

### Clone and Install Dependencies

```bash
# Navigate to project directory
cd CrawlStory

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configure Environment Variables

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your favorite editor
# Windows:
notepad .env
# Linux/Mac:
nano .env
```

Fill in the following values in `.env`:

```env
# === Supabase ===
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

# === Discord ===
DISCORD_BOT_TOKEN=your-bot-token-here
DISCORD_GUILD_ID=123456789012345678

# === Logging (Optional) ===
LOG_LEVEL=INFO
```

⚠️ **IMPORTANT**: Never commit `.env` to version control!

---

## 4️⃣ Running the Bot

### Start the Worker

```bash
# Ensure virtual environment is activated
python src/main.py
```

### Expected Output

```
2026-05-23 10:00:00 - __main__ - INFO - 🚀 CrawlStory Worker Starting...
2026-05-23 10:00:00 - __main__ - INFO - ✅ Database connection established
2026-05-23 10:00:00 - __main__ - INFO - Starting Discord bot for guild ID: 123456789012345678
2026-05-23 10:00:01 - bot.core - INFO - Bot logged in as CrawlStoryBot#1234 (ID: 987654321)
2026-05-23 10:00:01 - bot.core - INFO - Starting channel synchronization for guild: My Server (ID: 123456789012345678)
2026-05-23 10:00:02 - bot.core - INFO - Channel synchronization complete: 15/15 channels synced successfully
```

### Verify Channel Sync

1. Go to your Supabase project
2. Open **Table Editor** → `discord_channels`
3. You should see all your Discord text channels listed!

---

## 5️⃣ Troubleshooting

### Bot doesn't connect

**Error**: `Invalid Discord bot token`

**Solution**: 
- Verify your `DISCORD_BOT_TOKEN` in `.env`
- Regenerate the token in Discord Developer Portal if needed

---

### Guild not found

**Error**: `Guild with ID 123456789 not found`

**Solutions**:
- Verify `DISCORD_GUILD_ID` is correct (right-click server → Copy ID)
- Ensure the bot is invited to your server
- Check that the bot has "View Channels" permission

---

### Database connection failed

**Error**: `SUPABASE_URL environment variable is not set`

**Solutions**:
- Ensure `.env` file exists in the project root
- Verify all required variables are set
- Check for typos in variable names

---

### Channels not syncing

**Error**: `Failed to sync channel #general`

**Solutions**:
- Check Supabase table exists: `discord_channels`
- Verify the migration was run successfully
- Check Supabase logs for detailed error messages
- Ensure `service_role` key is used (not `anon` key)

---

## 6️⃣ Next Steps

Now that your bot is running and channels are synced:

1. **Add Social Media Targets** (Task A-6 - pending)
   - TikTok profiles, Instagram accounts, YouTube channels

2. **Configure AI Mappings** (Future task)
   - Let AI suggest which content goes to which channel
   - Approve/reject mappings via dashboard

3. **Set Up Dashboard** (Task K-4 - pending)
   - Web UI for managing everything
   - Real-time monitoring of scraped videos

---

## 🔒 Security Best Practices

- ✅ Never commit `.env` files to git
- ✅ Use `service_role` key only on the VPS (never in browser)
- ✅ Rotate tokens if accidentally exposed
- ✅ Use environment-specific `.env` files for dev/staging/prod
- ✅ Enable Supabase RLS policies for production

---

## 📚 Additional Resources

- [Discord.py Documentation](https://discordpy.readthedocs.io/)
- [Supabase Documentation](https://supabase.com/docs)
- [Project Architecture](ARCHITECTURE-SPEC.md)
- [Coding Standards](RULES.md)

---

## 🆘 Getting Help

If you encounter issues:

1. Check the logs for detailed error messages
2. Review `WORKING-CONTEXT.md` for known issues
3. Verify all environment variables are set correctly
4. Ensure database migration was run successfully

---

**Happy Scraping! 🎬**
