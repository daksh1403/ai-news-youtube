import { createClient } from "@libsql/client";

// In production (Vercel): use Turso
// In local dev: fall back to local SQLite file
const url = process.env.TURSO_DATABASE_URL || "file:../news_pipeline.db";
const authToken = process.env.TURSO_AUTH_TOKEN || undefined;

const db = createClient({
  url,
  authToken,
});

export interface PipelineRun {
  id: number;
  run_id: string;
  started_at: string;
  completed_at: string;
  status: string;
  articles_collected: number;
  scripts_generated: number;
  videos_produced: number;
  videos_uploaded: number;
  errors: string;
  duration_seconds: number;
}

export interface Upload {
  id: number;
  video_id: string;
  youtube_video_id: string;
  youtube_url: string;
  title: string;
  description: string;
  tags: string;
  category: string;
  privacy_status: string;
  uploaded_at: string;
  upload_status: string;
}

export interface Analytics {
  id: number;
  upload_id: string;
  views: number;
  watch_time_seconds: number;
  average_view_duration: number;
  click_through_rate: number;
  subscriber_growth: number;
  likes: number;
  comments: number;
  shares: number;
  collected_at: string;
}

export async function getRecentRuns(limit = 20): Promise<PipelineRun[]> {
  const result = await db.execute({
    sql: "SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT ?",
    args: [limit],
  });
  return result.rows as unknown as PipelineRun[];
}

export async function getTodayRuns(): Promise<PipelineRun[]> {
  const result = await db.execute({
    sql: "SELECT * FROM pipeline_runs WHERE date(started_at) = date('now') ORDER BY started_at DESC",
    args: [],
  });
  return result.rows as unknown as PipelineRun[];
}

export async function getRecentUploads(limit = 20): Promise<Upload[]> {
  const result = await db.execute({
    sql: "SELECT * FROM uploads ORDER BY uploaded_at DESC LIMIT ?",
    args: [limit],
  });
  return result.rows as unknown as Upload[];
}

export async function getTodayUploads(): Promise<Upload[]> {
  const result = await db.execute({
    sql: "SELECT * FROM uploads WHERE date(uploaded_at) = date('now') ORDER BY uploaded_at DESC",
    args: [],
  });
  return result.rows as unknown as Upload[];
}

export async function getStats() {
  const [totalRuns, todayRuns, totalUploads, todayUploads, totalArticles] =
    await Promise.all([
      db.execute("SELECT COUNT(*) as count FROM pipeline_runs"),
      db.execute(
        "SELECT COUNT(*) as count FROM pipeline_runs WHERE date(started_at) = date('now')"
      ),
      db.execute("SELECT COUNT(*) as count FROM uploads"),
      db.execute(
        "SELECT COUNT(*) as count FROM uploads WHERE date(uploaded_at) = date('now')"
      ),
      db.execute("SELECT COUNT(*) as count FROM used_articles"),
    ]);

  const successRuns = await db.execute(
    "SELECT COUNT(*) as count FROM pipeline_runs WHERE status = 'completed'"
  );

  const latestRun = await db.execute(
    "SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT 1"
  );

  return {
    totalRuns: Number(totalRuns.rows[0]?.count ?? 0),
    todayRuns: Number(todayRuns.rows[0]?.count ?? 0),
    totalUploads: Number(totalUploads.rows[0]?.count ?? 0),
    todayUploads: Number(todayUploads.rows[0]?.count ?? 0),
    totalArticles: Number(totalArticles.rows[0]?.count ?? 0),
    successRate:
      Number(totalRuns.rows[0]?.count ?? 0) > 0
        ? Math.round(
            (Number(successRuns.rows[0]?.count ?? 0) /
              Number(totalRuns.rows[0]?.count ?? 1)) *
              100
          )
        : 0,
    latestRun: (latestRun.rows[0] ?? null) as unknown as PipelineRun | null,
  };
}
