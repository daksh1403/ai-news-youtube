import re
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ModerationResult:
    allowed: bool
    reason: str = ""
    severity: str = "none"


BLOCKED_PATTERNS = {
    "nsfw": [
        r"\b(porn|xxx|nude|nsfw|sex\s*chat|adult\s*content|onlyfans)\b",
        r"\b(hentai|erotic|explicit\s*content)\b",
    ],
    "violence": [
        r"\b(gore|graphic\s*violence|brutal\s*murder|torture\s*video)\b",
        r"\b(active\s*shooter|mass\s*shooting\s*instructions)\b",
    ],
    "self_harm": [
        r"\b(kill\s*yourself|suicide\s*method|how\s*to\s*commit\s*suicide)\b",
        r"\b(self[\s-]*harm\s*tutorial|cutting\s*guide)\b",
    ],
    "illegal": [
        r"\b(how\s*to\s*make\s*(a\s*)?bomb|explosive\s*recipe)\b",
        r"\b(drug\s*synthesis|meth\s*recipe|fentanyl\s*pressing)\b",
        r"\b(child\s*abuse|csam|child\s*exploitation)\b",
    ],
    "hate": [
        r"\b(ethnic\s*cleansing|genocide\s*manual|racial\s*purification)\b",
    ],
    "scams": [
        r"\b(get\s*rich\s*quick\s*guaranteed|100%\s*profit\s*crypto)\b",
        r"\b(send\s*me\s*bitcoin\s*and\s*I.ll\s*double)\b",
    ],
}

SPAM_PATTERNS = [
    r"(subscribe\s*to\s*my\s*channel\s*\d+\s*times)",
    r"(follow\s*me\s*on\s*(onlyfans|fansly|patreon))",
    r"(use\s*my\s*discount\s*code\s*\w+)",
    r"(buy\s*now\s*limited\s*time\s*offer\s*\d+)",
]

SENSITIVE_TOPICS = [
    "election", "political", "gun control", "abortion",
    "religion", "cult", "conspiracy", "flat earth",
    "anti-vax", "covid hoax", "climate hoax",
]


def moderate_content(
    title: str,
    content: str,
    source: str = "",
    strict: bool = True,
) -> ModerationResult:
    text = f"{title} {content}".lower()

    for category, patterns in BLOCKED_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"BLOCKED [{category}]: {title[:60]}")
                return ModerationResult(
                    allowed=False,
                    reason=f"Blocked: {category} content detected",
                    severity="critical",
                )

    for pattern in SPAM_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            logger.warning(f"BLOCKED [spam]: {title[:60]}")
            return ModerationResult(
                allowed=False,
                reason="Blocked: promotional spam detected",
                severity="high",
            )

    if strict:
        for topic in SENSITIVE_TOPICS:
            if topic in text:
                logger.info(f"FLAGGED [sensitive]: {title[:60]} — topic: {topic}")
                return ModerationResult(
                    allowed=True,
                    reason=f"Sensitive topic: {topic}",
                    severity="medium",
                )

    if len(title.strip()) < 10:
        return ModerationResult(
            allowed=False,
            reason="Title too short (< 10 chars)",
            severity="medium",
        )

    if len(content.strip()) < 50:
        return ModerationResult(
            allowed=False,
            reason="Content too short (< 50 chars)",
            severity="medium",
        )

    if title.isupper() and len(title) > 20:
        return ModerationResult(
            allowed=True,
            reason="ALL CAPS title — may appear spammy",
            severity="low",
        )

    if title.count("!") > 3 or title.count("?") > 3:
        return ModerationResult(
            allowed=True,
            reason="Excessive punctuation in title",
            severity="low",
        )

    return ModerationResult(allowed=True, severity="none")


def sanitize_for_display(text: str, max_length: int = 200) -> str:
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'["\';`\\]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:max_length]


def sanitize_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', '_', name)
    return name[:100]
