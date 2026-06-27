import sys
import sqlite3
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import init_db

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

SOURCES = [
    # ═══════════════════════════════════════════════════════════════
    # 🇺🇸 UNITED STATES — AI & Tech
    # ═══════════════════════════════════════════════════════════════
    ("arxiv_ai", "http://arxiv.org/rss/cs.AI", "rss", "ai", 0.95),
    ("arxiv_cl", "http://arxiv.org/rss/cs.CL", "rss", "ai", 0.95),
    ("techcrunch_ai", "https://techcrunch.com/category/artificial-intelligence/feed/", "rss", "ai", 0.85),
    ("venturebeat_ai", "https://venturebeat.com/category/ai/feed/", "rss", "ai", 0.80),
    ("the_verge_ai", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "rss", "ai", 0.80),
    ("mit_tech_ai", "https://www.technologyreview.com/feed/", "rss", "ai", 0.90),
    ("openai_blog", "https://openai.com/blog/rss.xml", "rss", "ai", 0.90),
    ("huggingface_blog", "https://huggingface.co/blog/feed.xml", "rss", "ai", 0.90),
    ("techcrunch", "https://techcrunch.com/feed/", "rss", "tech", 0.85),
    ("the_verge", "https://www.theverge.com/rss/index.xml", "rss", "tech", 0.80),
    ("arstechnica", "https://feeds.arstechnica.com/arstechnica/index", "rss", "tech", 0.85),
    ("wired", "https://www.wired.com/feed/rss", "rss", "tech", 0.80),
    ("engadget", "https://www.engadget.com/rss.xml", "rss", "tech", 0.75),
    ("mashable", "https://mashable.com/feeds/rss/all", "rss", "tech", 0.75),
    ("cnn_top", "http://rss.cnn.com/rss/edition.rss", "rss", "world", 0.85),
    ("nytimes_home", "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml", "rss", "world", 0.90),
    ("nytimes_tech", "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml", "rss", "tech", 0.90),
    ("cnbc_top", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114", "rss", "business", 0.85),
    ("cnbc_tech", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19854910", "rss", "tech", 0.80),
    ("abc_news", "https://abcnews.go.com/abcnews/topstories", "rss", "world", 0.85),
    ("usatoday", "https://rssfeeds.usatoday.com/usatoday-NewsTopStories", "rss", "world", 0.80),
    ("fox_news", "https://moxie.foxnews.com/google-publisher/world.xml", "rss", "world", 0.75),

    # ═══════════════════════════════════════════════════════════════
    # 🇬🇧 UNITED KINGDOM
    # ═══════════════════════════════════════════════════════════════
    ("bbc_world", "https://feeds.bbci.co.uk/news/world/rss.xml", "rss", "world", 0.90),
    ("bbc_tech", "https://feeds.bbci.co.uk/news/technology/rss.xml", "rss", "tech", 0.85),
    ("bbc_sport", "https://feeds.bbci.co.uk/sport/rss.xml", "rss", "sports", 0.85),
    ("guardian_world", "https://www.theguardian.com/world/rss", "rss", "world", 0.85),
    ("guardian_tech", "https://www.theguardian.com/technology/rss", "rss", "tech", 0.80),
    ("independent", "https://www.independent.co.uk/news/world/rss", "rss", "world", 0.80),
    ("telegraph", "https://www.telegraph.co.uk/rss.xml", "rss", "world", 0.75),

    # ═══════════════════════════════════════════════════════════════
    # 🇮🇳 INDIA
    # ═══════════════════════════════════════════════════════════════
    ("the_hindu", "https://www.thehindu.com/feeder/default.rss", "rss", "world", 0.85),
    ("firstpost", "https://www.firstpost.com/feed/rss", "rss", "world", 0.80),
    ("times_of_india", "https://timesofindia.indiatimes.com/rssfeedstopnews.cms", "rss", "world", 0.80),
    ("ndtv", "https://feeds.feedburner.com/ndtvnews-top-stories", "rss", "world", 0.85),
    ("india_today", "https://www.indiatoday.in/rss/home", "rss", "world", 0.80),
    ("hindustan_times", "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml", "rss", "world", 0.80),
    ("indian_express", "https://indianexpress.com/feed/", "rss", "world", 0.80),
    ("moneycontrol", "https://www.moneycontrol.com/rss/marketnews.xml", "rss", "business", 0.80),
    ("economic_times", "https://economictimes.indiatimes.com/rssfeedstopstories.cms", "rss", "business", 0.80),
    ("the_print", "https://theprint.in/feed/", "rss", "world", 0.75),
    ("scroll", "https://scroll.in/feed", "rss", "world", 0.75),
    ("republic_world", "https://www.republicworld.com/rss/world-news.xml", "rss", "world", 0.75),
    ("wion", "https://www.wionews.com/feeds/world/rss.xml", "rss", "world", 0.75),
    ("ndeitech", "https://www.ndtv.com/feeds/rss/technology-news.xml", "rss", "tech", 0.80),

    # ═══════════════════════════════════════════════════════════════
    # 🌍 MIDDLE EAST
    # ═══════════════════════════════════════════════════════════════
    ("al_jazeera", "https://www.aljazeera.com/xml/rss/all.xml", "rss", "world", 0.85),

    # ═══════════════════════════════════════════════════════════════
    # 🇩🇪 GERMANY
    # ═══════════════════════════════════════════════════════════════
    ("deutsche_welle", "https://rss.dw.com/rdf/rss-en-all", "rss", "world", 0.85),
    ("spiegel", "https://www.spiegel.de/international/index.rss", "rss", "world", 0.80),

    # ═══════════════════════════════════════════════════════════════
    # 🇫🇷 FRANCE
    # ═══════════════════════════════════════════════════════════════
    ("france24", "https://www.france24.com/en/rss", "rss", "world", 0.85),
    ("le_monde", "https://www.lemonde.fr/rss/une.xml", "rss", "world", 0.80),

    # ═══════════════════════════════════════════════════════════════
    # 🇯🇵 JAPAN
    # ═══════════════════════════════════════════════════════════════
    ("nhk_world", "https://www3.nhk.or.jp/rss/news/cat0.xml", "rss", "world", 0.85),
    ("japantimes", "https://www.japantimes.co.jp/feed/", "rss", "world", 0.80),

    # ═══════════════════════════════════════════════════════════════
    # 🇰🇷 SOUTH KOREA
    # ═══════════════════════════════════════════════════════════════
    ("korea_times", "https://www.koreatimes.co.kr/www/rss/all.xml", "rss", "world", 0.75),

    # ═══════════════════════════════════════════════════════════════
    # 🇸🇬 SINGAPORE
    # ═══════════════════════════════════════════════════════════════
    ("channel_news_asia", "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml", "rss", "world", 0.80),

    # ═══════════════════════════════════════════════════════════════
    # 🇨🇳 CHINA / HONG KONG
    # ═══════════════════════════════════════════════════════════════
    ("scmp", "https://www.scmp.com/rss/91/feed", "rss", "world", 0.80),
    ("chinadaily", "https://www.chinadaily.com.cn/rss/world_rss.xml", "rss", "world", 0.70),

    # ═══════════════════════════════════════════════════════════════
    # 🇦🇺 AUSTRALIA
    # ═══════════════════════════════════════════════════════════════
    ("abc_australia", "https://www.abc.net.au/news/feed/51120/rss.xml", "rss", "world", 0.80),
    ("sydney_morning_herald", "https://www.smh.com.au/rss/feed.xml", "rss", "world", 0.80),

    # ═══════════════════════════════════════════════════════════════
    # 🇨🇦 CANADA
    # ═══════════════════════════════════════════════════════════════
    ("cbc_canada", "https://www.cbc.ca/webfeed/rss/rss-topstories", "rss", "world", 0.80),
    ("globe_mail", "https://www.theglobeandmail.com/arc/outboundfeeds/rss/?outputType=xml", "rss", "world", 0.75),

    # ═══════════════════════════════════════════════════════════════
    # 🇧🇷 BRAZIL
    # ═══════════════════════════════════════════════════════════════
    ("folha_brazil", "https://feeds.folha.uol.com.br/emcimadahora/rss091.xml", "rss", "world", 0.75),

    # ═══════════════════════════════════════════════════════════════
    # 🇿🇦 AFRICA
    # ═══════════════════════════════════════════════════════════════
    ("daily_maverick", "https://www.dailymaverick.co.za/dmrss/", "rss", "world", 0.75),
    ("mail_guardian", "https://www.news24.com/news24/feeds/rss", "rss", "world", 0.70),

    # ═══════════════════════════════════════════════════════════════
    # 🇪🇺 EUROPE (Other)
    # ═══════════════════════════════════════════════════════════════
    ("rt", "https://www.rt.com/rss/news/", "rss", "world", 0.70),
    ("euronews", "https://www.euronews.com/rss", "rss", "world", 0.80),
    ("bbc_europe", "https://feeds.bbci.co.uk/news/world/europe/rss.xml", "rss", "world", 0.85),

    # ═══════════════════════════════════════════════════════════════
    # 🔬 SCIENCE (Global)
    # ═══════════════════════════════════════════════════════════════
    ("science_daily", "https://www.sciencedaily.com/rss/all.xml", "rss", "science", 0.85),
    ("nature_news", "https://www.nature.com/nature.rss", "rss", "science", 0.90),
    ("space", "https://www.space.com/feeds/all", "rss", "science", 0.80),
    ("phys_org", "https://phys.org/rss-feed/", "rss", "science", 0.80),
    ("new_scientist", "https://www.newscientist.com/feed/home", "rss", "science", 0.85),

    # ═══════════════════════════════════════════════════════════════
    # 🎬 ENTERTAINMENT & SPORTS
    # ═══════════════════════════════════════════════════════════════
    ("variety", "https://variety.com/feed/", "rss", "entertainment", 0.80),
    ("hollywood_reporter", "https://www.hollywoodreporter.com/feed/", "rss", "entertainment", 0.80),
    ("deadline", "https://deadline.com/feed/", "rss", "entertainment", 0.75),
    ("espn", "https://www.espn.com/espn/rss/news", "rss", "sports", 0.85),
    ("skysports", "https://www.skysports.com/rss/12040", "rss", "sports", 0.80),
    ("bollywood_hungama", "https://www.bollywoodhungama.com/rss/news.xml", "rss", "entertainment", 0.75),
]


def seed():
    db_path = "news_pipeline.db"
    init_db(db_path)

    conn = sqlite3.connect(db_path)
    for name, url, src_type, category, score in SOURCES:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO sources (name, url, type, category, reliability_score) VALUES (?, ?, ?, ?, ?)",
                (name, url, src_type, category, score),
            )
        except Exception as e:
            logger.warning(f"Skip {name}: {e}")

    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    conn.close()
    logger.info(f"{count} sources in database")


if __name__ == "__main__":
    seed()
