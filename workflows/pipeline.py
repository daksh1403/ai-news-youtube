import uuid
import logging
from langgraph.graph import StateGraph, END
from agents.state import PipelineState
from agents.collector import NewsCollectorAgent
from agents.trend_detector import TrendDetectorAgent
from agents.verifier import FactVerificationAgent
from agents.ranker import NewsRankingAgent
from agents.seo import SEOAgent
from agents.scriptwriter import ScriptWriterAgent
from agents.reviewer import QualityReviewAgent
from agents.thumbnail import ThumbnailAgent
from agents.narrator import NarrationAgent
from agents.video import VideoAgent
from agents.uploader import UploadAgent
from agents.analytics import AnalyticsAgent
from agents.learner import LearningAgent

logger = logging.getLogger(__name__)


def build_pipeline(config=None):
    collector = NewsCollectorAgent(
        db_path=config.database_path if config else "news_pipeline.db",
        verification_limit=config.max_articles_per_run if config else 50,
    )
    trend = TrendDetectorAgent()
    verifier = FactVerificationAgent(
        db_path=config.database_path if config else "news_pipeline.db",
    )
    ranker = NewsRankingAgent()
    seo = SEOAgent()
    scriptwriter = ScriptWriterAgent()
    reviewer = QualityReviewAgent()
    thumbnail = ThumbnailAgent()
    narrator = NarrationAgent(
        engine=config.tts_engine if config else "edge-tts",
        voice=config.tts_voice if config else "en-US-GuyNeural",
    )
    video = VideoAgent()
    uploader = UploadAgent()
    analytics = AnalyticsAgent(
        db_path=config.database_path if config else "news_pipeline.db",
    )
    learner = LearningAgent(
        db_path=config.database_path if config else "news_pipeline.db",
    )

    graph = StateGraph(PipelineState)

    graph.add_node("collector", collector.collect)
    graph.add_node("trend_detector", trend.detect)
    graph.add_node("verifier", verifier.verify)
    graph.add_node("ranker", ranker.rank)
    graph.add_node("seo_optimizer", seo.optimize)
    graph.add_node("scriptwriter", scriptwriter.write_script)
    graph.add_node("reviewer", reviewer.review)
    graph.add_node("thumbnail", thumbnail.generate)
    graph.add_node("narrator", narrator.narrate)
    graph.add_node("video", video.assemble)
    graph.add_node("uploader", uploader.upload)
    graph.add_node("analytics", analytics.analyze)
    graph.add_node("learner", learner.learn)

    graph.set_entry_point("collector")

    graph.add_edge("collector", "trend_detector")
    graph.add_edge("trend_detector", "verifier")
    graph.add_edge("verifier", "ranker")
    graph.add_edge("ranker", "seo_optimizer")
    graph.add_edge("seo_optimizer", "scriptwriter")
    graph.add_edge("scriptwriter", "reviewer")

    def route_review(state):
        review = state.get("script_review", {})
        retry = state.get("retry_count", 0)
        if not review.get("approved") and retry < 3:
            return "scriptwriter"
        return "thumbnail"

    graph.add_conditional_edges("reviewer", route_review, {
        "scriptwriter": "scriptwriter",
        "thumbnail": "thumbnail",
    })

    graph.add_edge("thumbnail", "narrator")
    graph.add_edge("narrator", "video")
    graph.add_edge("video", "uploader")
    graph.add_edge("uploader", "analytics")
    graph.add_edge("analytics", "learner")
    graph.add_edge("learner", END)

    return graph.compile()


async def run_pipeline(mode: str = "daily_news", config=None) -> dict:
    run_id = str(uuid.uuid4())[:8]
    logger.info(f"AI NEWS PIPELINE — Run {run_id} — Mode: {mode}")

    pipeline = build_pipeline(config)

    initial_state: PipelineState = {
        "run_id": run_id,
        "mode": mode,
        "raw_articles": [],
        "deduplicated_articles": [],
        "verified_articles": [],
        "ranked_articles": [],
        "selected_article": {},
        "trends": [],
        "script": {},
        "script_review": {},
        "thumbnail_prompt": "",
        "thumbnail_url": "",
        "visual_plan": [],
        "seo_metadata": {},
        "audio_path": "",
        "subtitle_path": "",
        "video_path": "",
        "youtube_video_id": "",
        "youtube_url": "",
        "performance_data": {},
        "learning_insights": {},
        "current_step": "collector",
        "errors": [],
        "retry_count": 0,
        "completed": False,
        "blocked_count": 0,
        "flagged_count": 0,
        "review_queue_size": 0,
        "content_moderation_strict": config.content_moderation_strict if config else True,
        "verification_limit": config.max_articles_per_run if config else 50,
        "auto_upload": config.auto_upload if config else False,
        "review_before_upload": config.review_before_upload if config else True,
    }

    try:
        result = await pipeline.ainvoke(initial_state)
        logger.info(f"PIPELINE COMPLETE - Run {run_id}")
        logger.info(f"Video: {result.get('video_path', 'N/A')}")
        logger.info(f"YouTube: {result.get('youtube_url', 'N/A')}")
        logger.info(f"Errors: {len(result.get('errors', []))}")
        return result
    except Exception as e:
        logger.error(f"PIPELINE FAILED - Run {run_id}: {e}")
        return {"error": str(e), "run_id": run_id, "completed": False}
