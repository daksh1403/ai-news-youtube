# AI News Pipeline — Monitoring Dashboard

A Next.js dashboard for monitoring your AI news video pipeline, deployed on Vercel with Turso (managed SQLite).

## Features

- **Today's overview** — run count, upload count, success rate
- **Today's pipeline runs** — status, articles, videos, duration
- **Recent uploads** — YouTube links, upload status
- **All runs history** — full pipeline run log

## Setup

### 1. Create a Turso database

```bash
# Install Turso CLI
curl -sSfL https://get.tur.so/install.sh | bash

# Login and create database
turso auth login
turso db create ai-news-pipeline

# Get credentials
turso db show ai-news-pipeline --url
turso db tokens create ai-news-pipeline
```

### 2. Set Vercel environment variables

In your Vercel project settings, add:

```
TURSO_DATABASE_URL=libsql://ai-news-pipeline-your-org.turso.io
TURSO_AUTH_TOKEN=your-auth-token
```

Also add these to your GitHub Actions secrets for the sync step:

```
TURSO_DATABASE_URL=libsql://ai-news-pipeline-your-org.turso.io
TURSO_AUTH_TOKEN=your-auth-token
```

### 3. Deploy to Vercel

```bash
cd dashboard
npm install
npx vercel
```

Or connect the `dashboard/` directory to Vercel via the dashboard.

### 4. Data sync

The pipeline automatically syncs data to Turso after each run via GitHub Actions (`scripts/sync_turso.py`). The dashboard reads from Turso on each page load.

## Local development

```bash
cd dashboard
cp .env.example .env.local
# Fill in your Turso credentials
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).
