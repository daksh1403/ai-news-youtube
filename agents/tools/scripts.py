import json
import random


CATEGORY_TEMPLATES = {
    "ai": {
        "hooks": [
            "This AI breakthrough changes everything!",
            "AI just did something incredible!",
            "The AI race just shifted!",
            "This is huge for artificial intelligence!",
            "AI researchers are stunned!",
        ],
        "bridges": [
            "Here's what happened and why it matters.",
            "Let me break this down in 30 seconds.",
            "This is the biggest AI story this week.",
            "And it's about to change how we work.",
        ],
        "ctas": [
            "Follow for daily AI updates!",
            "Subscribe if you want to stay ahead!",
            "Drop a comment — what do you think?",
            "Follow for more AI news!",
        ],
    },
    "tech": {
        "hooks": [
            "Breaking tech news you need to see!",
            "This just dropped and it's massive!",
            "The tech world is buzzing about this!",
            "This changes the game for tech!",
        ],
        "bridges": [
            "Here's the deal.",
            "Let me explain why this matters.",
            "This is actually a big deal.",
            "Here's what you need to know.",
        ],
        "ctas": [
            "Follow for more tech news!",
            "Subscribe — you don't want to miss this!",
            "Like if this blew your mind!",
        ],
    },
    "world": {
        "hooks": [
            "Happening right now — this is major!",
            "Breaking news from around the world!",
            "This just in and it's significant!",
            "World events are shifting fast!",
        ],
        "bridges": [
            "Here's what's going on.",
            "Let me give you the quick version.",
            "Here's why the world is watching.",
        ],
        "ctas": [
            "Follow for world news updates!",
            "Stay informed — follow now!",
            "Share this if it matters to you!",
        ],
    },
    "science": {
        "hooks": [
            "Scientists just made a breakthrough!",
            "This discovery changes everything we know!",
            "Science just leveled up!",
            "Researchers found something incredible!",
        ],
        "bridges": [
            "Here's why this is a big deal.",
            "Let me explain the science simply.",
            "This could change how we understand the world.",
        ],
        "ctas": [
            "Follow for science news!",
            "Subscribe — science is wild!",
            "Tag someone who needs to see this!",
        ],
    },
    "business": {
        "hooks": [
            "Markets are reacting to this right now!",
            "This is reshaping the business world!",
            "Breaking business news!",
            "This deal just changed the industry!",
        ],
        "bridges": [
            "Here's what investors need to know.",
            "Let me break down the numbers.",
            "Here's the business impact.",
        ],
        "ctas": [
            "Follow for market updates!",
            "Subscribe for daily business news!",
            "Like if you're watching the markets!",
        ],
    },
    "entertainment": {
        "hooks": [
            "You won't believe what just happened!",
            "This is the biggest entertainment story right now!",
            "Hollywood is buzzing about this!",
            "Fans are going crazy over this!",
        ],
        "bridges": [
            "Here's the tea.",
            "Let me tell you what went down.",
            "Here's the full story.",
        ],
        "ctas": [
            "Follow for entertainment news!",
            "Subscribe — you don't want to miss this!",
            "Comment your reaction!",
        ],
    },
    "sports": {
        "hooks": [
            "What a moment in sports!",
            "This just happened and it's unreal!",
            "Sports fans are losing it right now!",
            "This is the play everyone's talking about!",
        ],
        "bridges": [
            "Here's what went down.",
            "Let me break down the highlights.",
            "Here's why this matters.",
        ],
        "ctas": [
            "Follow for sports updates!",
            "Subscribe — game day every day!",
            "Like if you're a true fan!",
        ],
    },
}

DEFAULT_TEMPLATE = CATEGORY_TEMPLATES["ai"]


def build_script_from_article(article: dict) -> dict:
    title = article.get("title", "Breaking news")
    content = article.get("content", "")
    category = article.get("category", "general")

    templates = CATEGORY_TEMPLATES.get(category, DEFAULT_TEMPLATE)
    hook = random.choice(templates["hooks"])
    bridge = random.choice(templates["bridges"])
    cta = random.choice(templates["ctas"])

    sentences = [s.strip() for s in content.split(".") if len(s.strip()) > 15]
    body_sentences = sentences[:5]
    body = ". ".join(body_sentences)
    if body and not body.endswith("."):
        body += "."

    if len(body) > 500:
        body = body[:500].rsplit(" ", 1)[0] + "."

    full_script = f"{hook} {title}. {bridge} {body} {cta}"

    words = full_script.split()
    if len(words) > 170:
        words = words[:170]
        full_script = " ".join(words)

    word_count = len(words)
    duration = min(59, max(10, int(word_count * 0.4)))

    return {
        "hook": hook,
        "sections": [
            {"title": "Hook", "content": hook, "duration_seconds": 3},
            {"title": "Context", "content": f"{title}. {bridge}", "duration_seconds": 8},
            {"title": "Body", "content": body, "duration_seconds": duration - 16},
            {"title": "CTA", "content": cta, "duration_seconds": 5},
        ],
        "cta": cta,
        "full_script": full_script,
        "word_count": word_count,
        "estimated_duration": duration,
    }


def build_trend_script(trend: dict) -> dict:
    topic = trend.get("topic", "Breaking news")
    category = trend.get("category", "general")
    templates = CATEGORY_TEMPLATES.get(category, DEFAULT_TEMPLATE)

    hook = random.choice(templates["hooks"])
    bridge = random.choice(templates["bridges"])
    cta = random.choice(templates["ctas"])

    full_script = f"{hook} {topic}. {bridge} This is one of the top trending stories right now. {cta}"
    words = full_script.split()
    word_count = len(words)
    duration = min(59, max(10, int(word_count * 0.4)))

    return {
        "hook": hook,
        "sections": [
            {"title": "Hook", "content": hook, "duration_seconds": 3},
            {"title": "Body", "content": f"{topic}. {bridge}", "duration_seconds": duration - 8},
            {"title": "CTA", "content": cta, "duration_seconds": 5},
        ],
        "cta": cta,
        "full_script": full_script,
        "word_count": word_count,
        "estimated_duration": duration,
    }


def get_llm_fallback_response(prompt: str) -> str:
    return json.dumps({
        "hook": "Breaking news you need to know about",
        "sections": [
            {"title": "Hook", "content": "Breaking news you need to know about", "duration_seconds": 3},
            {"title": "Main Story", "content": "This is a developing story.", "duration_seconds": 30},
            {"title": "Why It Matters", "content": "Here's why this matters.", "duration_seconds": 15},
            {"title": "CTA", "content": "Follow for more!", "duration_seconds": 5},
        ],
        "cta": "Follow for more news!",
        "full_script": "Breaking news you need to know about. This is a developing story that matters. Follow for more news!",
        "word_count": 20,
        "estimated_duration": 55,
    })
