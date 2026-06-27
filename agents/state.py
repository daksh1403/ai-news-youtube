from typing import TypedDict, Annotated, List
import operator


class PipelineState(TypedDict, total=False):
    run_id: str
    mode: str

    raw_articles: List[dict]
    deduplicated_articles: List[dict]
    verified_articles: List[dict]
    ranked_articles: List[dict]
    selected_article: dict
    trends: List[dict]

    script: dict
    script_review: dict
    thumbnail_prompt: str
    thumbnail_url: str
    visual_plan: List[dict]
    seo_metadata: dict

    audio_path: str
    subtitle_path: str
    video_path: str

    youtube_video_id: str
    youtube_url: str

    performance_data: dict
    learning_insights: dict

    current_step: str
    errors: Annotated[List[str], operator.add]
    retry_count: int
    completed: bool

    blocked_count: int
    flagged_count: int
    review_queue_size: int
    content_moderation_strict: bool
    verification_limit: int
    auto_upload: bool
    review_before_upload: bool
