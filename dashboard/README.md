# CrawlStory Dashboard

Next.js 14 dashboard for managing social media video scraping and Discord delivery with AI-powered mapping suggestions.

## Features

- **Target Management**: Add and manage social media profiles to scrape
- **AI Mapping Approval**: Review and approve AI-suggested channel mappings
- **Real-time Updates**: Direct Supabase integration for instant data sync
- **Responsive Design**: Clean, modern UI built with Tailwind CSS

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Database**: Supabase (PostgreSQL)
- **Icons**: Lucide React
- **AI Algorithm**: Jaro-Winkler text similarity

## Getting Started

### Prerequisites

- Node.js 18+
- Supabase project with schema deployed
- Environment variables configured

### Installation

```bash
# Install dependencies
npm install

# Copy environment template
cp .env.local.example .env.local

# Edit .env.local with your Supabase credentials
```

### Environment Variables

Create `.env.local` with:

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_AI_CONFIDENCE_THRESHOLD=60
```

### Development

```bash
# Run development server
npm run dev

# Open http://localhost:3000
```

### Build for Production

```bash
# Build
npm run build

# Start production server
npm start
```

## Project Structure

```
dashboard/
├── src/
│   ├── app/
│   │   ├── page.tsx                    # Home page
│   │   ├── dashboard/
│   │   │   ├── targets/page.tsx        # Target management
│   │   │   └── approval/page.tsx       # AI mapping approval
│   │   ├── layout.tsx
│   │   └── globals.css
│   ├── components/
│   │   └── ui/
│   │       ├── Button.tsx              # Reusable button
│   │       └── Card.tsx                # Reusable card
│   ├── lib/
│   │   ├── supabase.ts                 # Supabase client
│   │   └── similarity.ts               # AI similarity algorithm
│   └── types/
│       └── database.ts                 # TypeScript types
├── package.json
├── tsconfig.json
├── tailwind.config.ts
└── next.config.js
```

## AI Mapping Algorithm

The dashboard uses **Jaro-Winkler similarity** to automatically suggest mappings between Discord channels and social media targets.

### How It Works

1. **Text Normalization**: Removes special characters, converts to lowercase
2. **Similarity Calculation**: Compares channel names, descriptions, and tags
3. **Weighted Scoring**:
   - Name similarity: 50%
   - Description similarity: 30%
   - Tag similarity: 20%
4. **Threshold Filtering**: Only suggests mappings above 60% confidence
5. **Auto-insertion**: Creates pending mappings in `ai_mappings` table

### Example

```typescript
Channel: "gaming-videos" + tags: ["gaming", "esports"]
Target: "@GamingPro" + description: "Professional gaming content"
Result: 85% match → Auto-suggested for approval
```

## Pages

### Home (`/`)

Landing page with navigation to:
- Manage Targets
- AI Mapping Approval

### Targets (`/dashboard/targets`)

**Features**:
- View all social media targets
- Add new targets (TikTok, Instagram, YouTube, Twitter)
- Delete existing targets
- Auto-triggers AI mapping on target creation

**Add Target Flow**:
1. User fills form (platform, username, description)
2. Target inserted into `social_targets` table
3. AI algorithm finds matching Discord channels
4. Pending mappings created in `ai_mappings` table

### Approval (`/dashboard/approval`)

**Features**:
- View all pending AI mapping suggestions
- See confidence scores and reasoning
- Approve mappings (enables video delivery)
- Reject mappings (prevents delivery)

**Mapping Card Shows**:
- Discord channel name and description
- Social media target and platform
- AI confidence score (color-coded)
- AI reasoning
- Approve/Reject buttons

## Deployment

### Vercel (Recommended)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Set environment variables in Vercel dashboard
```

### Environment Variables on Vercel

Add these in Project Settings → Environment Variables:
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_AI_CONFIDENCE_THRESHOLD`

## Development Guidelines

### Code Standards

- **File Limit**: Max 300 lines per file
- **Type Safety**: Full TypeScript with strict mode
- **Naming**: camelCase for functions, PascalCase for components
- **Styling**: Tailwind CSS utility classes
- **Components**: Modular, reusable UI components

### Adding New Pages

1. Create page in `src/app/dashboard/[name]/page.tsx`
2. Use `'use client'` directive for client components
3. Import types from `@/types/database`
4. Use Supabase client from `@/lib/supabase`

### Modifying AI Algorithm

Edit `src/lib/similarity.ts`:
- `jaroWinklerSimilarity()`: Core algorithm
- `calculateMappingScore()`: Scoring logic
- `findBestMatches()`: Matching logic

## Troubleshooting

### Supabase Connection Error

**Error**: "Missing Supabase environment variables"

**Solution**: Ensure `.env.local` exists with correct values

### No Mappings Appearing

**Issue**: Added target but no mappings suggested

**Causes**:
- No Discord channels in database (run bot first)
- Confidence score below threshold
- Channel/target names too dissimilar

**Solution**: Lower `NEXT_PUBLIC_AI_CONFIDENCE_THRESHOLD` or add more descriptive channel tags

### Build Errors

**Error**: Type errors during build

**Solution**: Run `npm run lint` and fix TypeScript errors

## Future Enhancements

- [ ] User authentication with Supabase Auth
- [ ] Real-time updates with Supabase Realtime
- [ ] Video history and analytics
- [ ] Bulk approval/rejection
- [ ] Custom mapping rules
- [ ] Dashboard statistics and charts

## License

Part of the CrawlStory project.
