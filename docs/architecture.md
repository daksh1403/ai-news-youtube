# System Architecture — 2 Videos/Day Never-Stop

## Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│              NEVER-STOP SCHEDULER (2x/day)                  │
│                                                             │
│  Run 1: 06:00    Run 2: 14:00    Retry: +5min on failure   │
│       │                │                  │                  │
│       └────────────────┴──────────────────┘                  │
│                         │                                   │
│                         ▼                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              LANGGRAPH PIPELINE                       │   │
│  │                                                      │   │
│  │  Collector → TrendDetector → Verifier → Ranker       │   │
│  │       → SEO → ScriptWriter ←→ Reviewer (loop)        │   │
│  │       → Thumbnail → Narrator → VideoAssembler        │   │
│  │       → Uploader → Analytics → Learner               │   │
│  └──────────────────────────────────────────────────────┘   │
│                         │                                   │
│                         ▼                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Groq API   │  │ Pollinations│  │  YouTube    │        │
│  │  (LLM free) │  │ (images)    │  │  Data API   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                             │
│  NEVER STOPS. If one run fails, next run still happens.     │
│  Scheduler loop: sleep → wake → run → sleep → ...           │
└─────────────────────────────────────────────────────────────┘
```

## Why It Never Stops

1. **Infinite loop**: `while running:` in scheduler — never exits
2. **Run isolation**: Each run is independent — failure doesn't affect next
3. **Retry logic**: 5-minute wait after critical failure, then resume
4. **Signal handling**: Only Ctrl+C stops it gracefully
5. **Stateless runs**: Each pipeline run is a fresh `PipelineState` dict
6. **GitHub Actions backup**: Cron triggers even if local scheduler is down

## 2 Videos/Day Schedule

| Time | Mode | Duration |
|------|------|----------|
| 06:00 | daily_news | ~15-20 min |
| 14:00 | daily_news | ~15-20 min |

Configurable via `PIPELINE_RUN_HOUR_1` and `PIPELINE_RUN_HOUR_2`.

## Failure Handling

```
Pipeline fails
    │
    ├─→ Log error to database
    ├─→ Record partial run
    ├─→ Wait 5 minutes
    └─→ Resume normal schedule (next run at configured time)
```

No cascading failures. Each run is independent.
