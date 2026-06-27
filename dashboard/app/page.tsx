import { getStats, getTodayRuns, getRecentUploads, getRecentRuns } from "@/lib/db";

function StatCard({
  label,
  value,
  sub,
  color = "blue",
}: {
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
}) {
  const colors: Record<string, string> = {
    blue: "from-blue-500/20 to-blue-600/5 border-blue-500/20",
    green: "from-emerald-500/20 to-emerald-600/5 border-emerald-500/20",
    amber: "from-amber-500/20 to-amber-600/5 border-amber-500/20",
    purple: "from-purple-500/20 to-purple-600/5 border-purple-500/20",
    red: "from-red-500/20 to-red-600/5 border-red-500/20",
    cyan: "from-cyan-500/20 to-cyan-600/5 border-cyan-500/20",
  };
  return (
    <div
      className={`bg-gradient-to-br ${colors[color]} border rounded-2xl p-6 flex flex-col gap-1`}
    >
      <span className="text-xs font-medium uppercase tracking-wider text-white/50">
        {label}
      </span>
      <span className="text-3xl font-bold text-white">{value}</span>
      {sub && <span className="text-sm text-white/40">{sub}</span>}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    completed: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
    running: "bg-blue-500/20 text-blue-400 border-blue-500/30",
    failed: "bg-red-500/20 text-red-400 border-red-500/30",
    partial: "bg-amber-500/20 text-amber-400 border-amber-500/30",
    pending: "bg-white/10 text-white/60 border-white/20",
  };
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${colors[status] || colors.pending}`}
    >
      {status}
    </span>
  );
}

function formatDuration(seconds: number | null) {
  if (!seconds) return "—";
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function formatTime(iso: string | null) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default async function DashboardPage() {
  let stats, todayRuns, recentUploads, recentRuns;

  try {
    [stats, todayRuns, recentUploads, recentRuns] = await Promise.all([
      getStats(),
      getTodayRuns(),
      getRecentUploads(10),
      getRecentRuns(15),
    ]);
  } catch (e) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <h1 className="text-2xl font-bold text-white">
            Dashboard Unavailable
          </h1>
          <p className="text-white/50 max-w-md">
            Could not connect to the database. Make sure{" "}
            <code className="bg-white/10 px-2 py-0.5 rounded">
              TURSO_DATABASE_URL
            </code>{" "}
            and{" "}
            <code className="bg-white/10 px-2 py-0.5 rounded">
              TURSO_AUTH_TOKEN
            </code>{" "}
            are set in your Vercel environment.
          </p>
          <pre className="text-xs text-red-400/80 bg-red-500/10 p-4 rounded-xl border border-red-500/20 max-w-lg text-left overflow-auto">
            {String(e)}
          </pre>
        </div>
      </div>
    );
  }

  const latestStatus = stats.latestRun?.status ?? "unknown";
  const latestTime = stats.latestRun
    ? formatTime(stats.latestRun.started_at)
    : "No runs yet";

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 py-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-sm">
              AI
            </div>
            <div>
              <h1 className="text-lg font-semibold text-white">
                AI News Pipeline
              </h1>
              <p className="text-xs text-white/40">
                Monitoring Dashboard
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <StatusBadge status={latestStatus} />
            <span className="text-xs text-white/30">Last: {latestTime}</span>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <StatCard
            label="Today's Runs"
            value={stats.todayRuns}
            sub={`of ${stats.totalRuns} total`}
            color="blue"
          />
          <StatCard
            label="Today's Uploads"
            value={stats.todayUploads}
            sub={`of ${stats.totalUploads} total`}
            color="green"
          />
          <StatCard
            label="Success Rate"
            value={`${stats.successRate}%`}
            color={stats.successRate >= 90 ? "green" : stats.successRate >= 70 ? "amber" : "red"}
          />
          <StatCard
            label="Total Articles"
            value={stats.totalArticles}
            sub="processed"
            color="purple"
          />
          <StatCard
            label="Latest Status"
            value={latestStatus}
            sub={latestTime}
            color={latestStatus === "completed" ? "green" : latestStatus === "failed" ? "red" : "blue"}
          />            <StatCard
              label="Videos/Day"
              value={2}
              sub="scheduled"
              color="cyan"
            />
        </div>

        {/* Today's Runs */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">
              Today&apos;s Pipeline Runs
            </h2>
            <span className="text-xs text-white/30">
              Auto-refreshes on deploy
            </span>
          </div>
          {todayRuns.length === 0 ? (
            <div className="glass rounded-2xl p-8 text-center">
              <p className="text-white/40">
                No runs today yet. Pipeline runs at 06:00 and 14:00.
              </p>
            </div>
          ) : (
            <div className="glass rounded-2xl overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/5">
                    <th className="text-left px-6 py-3 text-xs font-medium text-white/40 uppercase tracking-wider">
                      Run ID
                    </th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-white/40 uppercase tracking-wider">
                      Started
                    </th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-white/40 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-white/40 uppercase tracking-wider">
                      Articles
                    </th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-white/40 uppercase tracking-wider">
                      Videos
                    </th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-white/40 uppercase tracking-wider">
                      Duration
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {todayRuns.map((run) => (
                    <tr key={run.id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="px-6 py-3 font-mono text-xs text-white/70">
                        {run.run_id}
                      </td>
                      <td className="px-6 py-3 text-white/60">
                        {formatTime(run.started_at)}
                      </td>
                      <td className="px-6 py-3">
                        <StatusBadge status={run.status} />
                      </td>
                      <td className="px-6 py-3 text-white/60">
                        {run.articles_collected ?? 0}
                      </td>
                      <td className="px-6 py-3 text-white/60">
                        {run.videos_produced ?? 0}
                      </td>
                      <td className="px-6 py-3 text-white/60">
                        {formatDuration(run.duration_seconds)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* Recent Uploads */}
        <section className="space-y-4">
          <h2 className="text-lg font-semibold text-white">Recent Uploads</h2>
          {recentUploads.length === 0 ? (
            <div className="glass rounded-2xl p-8 text-center">
              <p className="text-white/40">No uploads yet.</p>
            </div>
          ) : (
            <div className="glass rounded-2xl overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/5">
                    <th className="text-left px-6 py-3 text-xs font-medium text-white/40 uppercase tracking-wider">
                      Title
                    </th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-white/40 uppercase tracking-wider">
                      YouTube ID
                    </th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-white/40 uppercase tracking-wider">
                      Uploaded
                    </th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-white/40 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-white/40 uppercase tracking-wider">
                      Link
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {recentUploads.map((upload) => (
                    <tr key={upload.id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="px-6 py-3 text-white/80 max-w-[300px] truncate">
                        {upload.title || "Untitled"}
                      </td>
                      <td className="px-6 py-3 font-mono text-xs text-white/50">
                        {upload.youtube_video_id
                          ? upload.youtube_video_id.slice(0, 12) + "…"
                          : "—"}
                      </td>
                      <td className="px-6 py-3 text-white/60">
                        {formatTime(upload.uploaded_at)}
                      </td>
                      <td className="px-6 py-3">
                        <StatusBadge status={upload.upload_status || "pending"} />
                      </td>
                      <td className="px-6 py-3">
                        {upload.youtube_url ? (
                          <a
                            href={upload.youtube_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-400 hover:text-blue-300 transition-colors underline underline-offset-2"
                          >
                            Watch →
                          </a>
                        ) : (
                          <span className="text-white/30">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* All Runs */}
        <section className="space-y-4">
          <h2 className="text-lg font-semibold text-white">
            All Pipeline Runs
          </h2>
          <div className="glass rounded-2xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/5">
                  <th className="text-left px-6 py-3 text-xs font-medium text-white/40 uppercase tracking-wider">
                    Run ID
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-white/40 uppercase tracking-wider">
                    Started
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-white/40 uppercase tracking-wider">
                    Completed
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-white/40 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-white/40 uppercase tracking-wider">
                    Articles
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-white/40 uppercase tracking-wider">
                    Scripts
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-white/40 uppercase tracking-wider">
                    Videos
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-white/40 uppercase tracking-wider">
                    Uploaded
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-white/40 uppercase tracking-wider">
                    Duration
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {recentRuns.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="px-6 py-8 text-center text-white/40">
                      No runs recorded yet.
                    </td>
                  </tr>
                ) : (
                  recentRuns.map((run) => (
                    <tr key={run.id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="px-6 py-3 font-mono text-xs text-white/70">
                        {run.run_id}
                      </td>
                      <td className="px-6 py-3 text-white/60">
                        {formatTime(run.started_at)}
                      </td>
                      <td className="px-6 py-3 text-white/60">
                        {formatTime(run.completed_at)}
                      </td>
                      <td className="px-6 py-3">
                        <StatusBadge status={run.status} />
                      </td>
                      <td className="px-6 py-3 text-white/60">
                        {run.articles_collected ?? 0}
                      </td>
                      <td className="px-6 py-3 text-white/60">
                        {run.scripts_generated ?? 0}
                      </td>
                      <td className="px-6 py-3 text-white/60">
                        {run.videos_produced ?? 0}
                      </td>
                      <td className="px-6 py-3 text-white/60">
                        {run.videos_uploaded ?? 0}
                      </td>
                      <td className="px-6 py-3 text-white/60">
                        {formatDuration(run.duration_seconds)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        {/* Footer */}
        <footer className="text-center py-8 text-xs text-white/20">
          AI News Pipeline Dashboard • Auto-refreshes on each pipeline run
        </footer>
      </main>
    </div>
  );
}
