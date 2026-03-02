import os
import re
import time
import json
import hashlib
import requests
import textwrap
from datetime import datetime
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import feedparser

# ── CONFIG ──────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8627795096:AAER3rfLzA7KCnRWduEvbxvERmulTVtB-eE")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "5233860632")
SENT_FILE = "sent_articles.json"

# Real Madrid RSS feeds (free, no API key needed)
RSS_FEEDS = [
    "https://feeds.feedburner.com/goal/realmadrid",
    "https://www.managingmadrid.com/rss/current",
    "https://realmadridnews.com/feed/",
    "https://www.101greatgoals.com/feed/category/real-madrid/",
    "https://feeds.feedburner.com/RealMadridLatestNews",
    "https://www.football-espana.net/feed",
    "https://www.madridistareal.net/feed",
]

# Fallback: GNews API (free tier 100 req/day)
GNEWS_URL = "https://gnews.io/api/v4/search"
GNEWS_KEY = os.environ.get("GNEWS_KEY", "")  # optional

# Colors - Real Madrid Premium Theme
WHITE     = (255, 255, 255)
GOLD      = (212, 175, 55)
DARK_GOLD = (160, 120, 20)
BLACK     = (10, 10, 10)
MADRID_PURPLE = (102, 51, 153)
DARK_BG   = (15, 15, 20)
CARD_BG   = (22, 22, 30)
ACCENT    = (212, 175, 55)

# ── HELPERS ─────────────────────────────────────────────────────────────────

def load_sent():
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE) as f:
            return set(json.load(f))
    return set()

def save_sent(sent):
    with open(SENT_FILE, "w") as f:
        json.dump(list(sent)[-200:], f)  # keep last 200

def article_id(url):
    return hashlib.md5(url.encode()).hexdigest()

# ── NEWS SCRAPING ────────────────────────────────────────────────────────────

def fetch_rss_articles():
    articles = []
    keywords = ["real madrid", "realmadrid", "madrid", "benzema", "vinicius",
                "bellingham", "ancelotti", "mbappé", "mbappe", "bernabeu",
                "kroos", "modric", "courtois", "rodrygo", "valverde"]
    
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0"})
            for entry in feed.entries[:5]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                link = entry.get("link", "")
                
                text = (title + " " + summary).lower()
                if any(kw in text for kw in keywords):
                    # Try to get image
                    image_url = None
                    if hasattr(entry, "media_content") and entry.media_content:
                        image_url = entry.media_content[0].get("url")
                    elif hasattr(entry, "enclosures") and entry.enclosures:
                        image_url = entry.enclosures[0].get("href")
                    
                    # Try from content
                    if not image_url:
                        content = entry.get("content", [{}])[0].get("value", "") if entry.get("content") else ""
                        imgs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', content + summary)
                        if imgs:
                            image_url = imgs[0]
                    
                    articles.append({
                        "title": title,
                        "summary": clean_html(summary)[:300],
                        "link": link,
                        "image_url": image_url,
                        "source": feed.feed.get("title", url.split("/")[2]),
                        "published": entry.get("published", "")
                    })
        except Exception as e:
            print(f"RSS error {url}: {e}")
    return articles

def clean_html(text):
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def fetch_gnews_articles():
    if not GNEWS_KEY:
        return []
    try:
        r = requests.get(GNEWS_URL, params={
            "q": "Real Madrid",
            "lang": "en",
            "max": 10,
            "apikey": GNEWS_KEY
        }, timeout=10)
        data = r.json()
        articles = []
        for a in data.get("articles", []):
            articles.append({
                "title": a["title"],
                "summary": a.get("description", "")[:300],
                "link": a["url"],
                "image_url": a.get("image"),
                "source": a["source"]["name"],
                "published": a.get("publishedAt", "")
            })
        return articles
    except Exception as e:
        print(f"GNews error: {e}")
        return []

def get_article_image(url):
    if not url:
        return None
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        img = Image.open(BytesIO(r.content)).convert("RGBA")
        return img
    except:
        return None

# ── IMAGE GENERATION ─────────────────────────────────────────────────────────

def generate_anime_image(article):
    """
    Uses Pollinations.ai (free, no key, reliable) to generate anime-styled image.
    Falls back to styling the original article image if generation fails.
    """
    title = article["title"]
    
    # Build a strong prompt for Pollinations
    prompt = (
        f"anime style illustration, Real Madrid football fan art, "
        f"scene depicting: {title[:80]}, "
        f"Spanish football stadium atmosphere, Santiago Bernabeu, "
        f"dramatic lighting, gold and white colors, "
        f"high quality anime art, detailed, cinematic composition, "
        f"no text, clean background"
    )
    
    encoded = requests.utils.quote(prompt)
    pollinations_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1080&model=flux&nologo=true&seed={int(time.time())}"
    
    print(f"Generating image via Pollinations: {pollinations_url[:100]}...")
    
    try:
        r = requests.get(pollinations_url, timeout=60)
        if r.status_code == 200 and len(r.content) > 10000:
            img = Image.open(BytesIO(r.content)).convert("RGBA")
            print("✅ Pollinations image generated successfully")
            return img
    except Exception as e:
        print(f"Pollinations failed: {e}")
    
    # Fallback: use original article image
    if article.get("image_url"):
        img = get_article_image(article["image_url"])
        if img:
            print("✅ Using original article image")
            return img
    
    # Last fallback: create a gradient background
    print("Using gradient fallback")
    img = Image.new("RGBA", (1080, 1080), DARK_BG)
    draw = ImageDraw.Draw(img)
    # Draw a simple gradient-like effect
    for i in range(1080):
        alpha = int(255 * (1 - i / 1080) * 0.3)
        draw.line([(0, i), (1080, i)], fill=(212, 175, 55, alpha))
    return img

def make_post_image(article):
    """Creates the full Instagram-style post image with premium Real Madrid branding."""
    
    POST_W, POST_H = 1080, 1350  # Instagram portrait format
    
    # 1. Get/generate the background image
    bg_img = generate_anime_image(article)
    bg_img = bg_img.convert("RGBA").resize((POST_W, POST_H), Image.LANCZOS)
    
    # 2. Create the canvas
    canvas = Image.new("RGBA", (POST_W, POST_H), DARK_BG)
    canvas.paste(bg_img, (0, 0))
    
    # 3. Apply dark overlay gradient (top and bottom) for text readability
    overlay = Image.new("RGBA", (POST_W, POST_H), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    
    # Top gradient (header area)
    for i in range(280):
        alpha = int(220 * (1 - i / 280))
        draw_ov.line([(0, i), (POST_W, i)], fill=(10, 10, 15, alpha))
    
    # Bottom gradient (content area)
    for i in range(POST_H - 650, POST_H):
        alpha = int(240 * ((i - (POST_H - 650)) / 650))
        draw_ov.line([(0, i), (POST_W, i)], fill=(10, 10, 15, alpha))
    
    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)
    
    # ── FONTS ──
    def get_font(size, bold=False):
        font_paths = [
            f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
            f"/usr/share/fonts/truetype/liberation/LiberationSans-{'Bold' if bold else 'Regular'}.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    return ImageFont.truetype(fp, size)
                except:
                    pass
        return ImageFont.load_default()
    
    font_brand   = get_font(28, bold=True)
    font_source  = get_font(22)
    font_headline= get_font(52, bold=True)
    font_body    = get_font(30)
    font_tag     = get_font(24, bold=True)
    font_footer  = get_font(22)
    
    # ── HEADER BAR ──
    # Gold top accent line
    draw.rectangle([(0, 0), (POST_W, 6)], fill=GOLD)
    
    # Logo / Brand name
    brand_text = "⚽ REAL MADRID ZONE"
    draw.text((50, 30), brand_text, font=font_brand, fill=GOLD)
    
    # Source badge
    source = article.get("source", "Football News")[:30]
    source_text = f"📡 {source}"
    draw.text((50, 68), source_text, font=font_source, fill=(180, 180, 180))
    
    # Date/time
    now = datetime.now().strftime("%b %d, %Y · %H:%M")
    draw.text((POST_W - 220, 68), now, font=font_source, fill=(150, 150, 150))
    
    # Thin gold separator line
    draw.rectangle([(50, 105), (POST_W - 50, 107)], fill=(212, 175, 55, 180))
    
    # ── BOTTOM CONTENT AREA ──
    content_y = POST_H - 640
    
    # "BREAKING" or "LATEST" tag
    tag_text = "  🏟 LATEST NEWS  "
    tag_w = draw.textlength(tag_text, font=font_tag)
    draw.rounded_rectangle([(50, content_y), (50 + tag_w + 10, content_y + 38)],
                            radius=6, fill=GOLD)
    draw.text((55, content_y + 4), tag_text, font=font_tag, fill=BLACK)
    
    content_y += 55
    
    # ── HEADLINE ──
    title = article["title"]
    # Word wrap headline
    words = title.split()
    lines = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        if draw.textlength(test, font=font_headline) < POST_W - 100:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
        if len(lines) >= 3:
            break
    if current and len(lines) < 3:
        lines.append(current)
    if len(lines) == 3 and current not in lines:
        lines[-1] = lines[-1][:30] + "..."
    
    # Shadow + text for headline
    for i, line in enumerate(lines[:3]):
        y = content_y + i * 65
        # Shadow
        draw.text((52, y + 2), line, font=font_headline, fill=(0, 0, 0, 200))
        draw.text((50, y), line, font=font_headline, fill=WHITE)
    
    content_y += len(lines) * 65 + 20
    
    # Gold divider
    draw.rectangle([(50, content_y), (POST_W // 2, content_y + 3)], fill=GOLD)
    content_y += 20
    
    # ── SUMMARY / ANALYSIS BULLETS ──
    summary = article.get("summary", "")
    if summary:
        # Split into ~2 key points
        sentences = re.split(r'[.!?]+', summary)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20][:3]
        
        for sent in sentences:
            if content_y > POST_H - 200:
                break
            # Wrap sentence
            wrapped = textwrap.wrap(sent, width=42)[:2]
            for j, wline in enumerate(wrapped):
                prefix = "▸ " if j == 0 else "   "
                draw.text((50, content_y), prefix + wline, font=font_body,
                          fill=(230, 230, 230))
                content_y += 38
            content_y += 5
    
    # ── FOOTER ──
    footer_y = POST_H - 80
    draw.rectangle([(0, footer_y - 10), (POST_W, footer_y - 8)], fill=(212, 175, 55, 120))
    
    hashtags = "#RealMadrid #HalaMadrid #UCL #LaLiga #RMCF #Football #Madrid"
    draw.text((50, footer_y), hashtags, font=font_footer, fill=(180, 180, 180))
    
    # Bottom gold line
    draw.rectangle([(0, POST_H - 6), (POST_W, POST_H)], fill=GOLD)
    
    # ── WATERMARK / CROWN ICON ──
    crown = "👑 Real Madrid Zone"
    cw = draw.textlength(crown, font=font_brand)
    draw.text((POST_W - cw - 50, POST_H - 105), crown, font=font_brand, fill=GOLD)
    
    # Convert to RGB for saving
    final = canvas.convert("RGB")
    return final

# ── TELEGRAM SENDER ──────────────────────────────────────────────────────────

def send_to_telegram(article, image: Image.Image):
    """Send the post image + caption to Telegram."""
    
    title = article["title"]
    summary = article.get("summary", "")
    source = article.get("source", "")
    link = article.get("link", "")
    
    caption = (
        f"👑 *REAL MADRID ZONE*\n\n"
        f"🏟 *{title}*\n\n"
        f"{summary[:300] + '...' if len(summary) > 300 else summary}\n\n"
        f"📡 Source: {source}\n"
        f"🔗 [Read Full Article]({link})\n\n"
        f"#RealMadrid #HalaMadrid #UCL #LaLiga #RMCF"
    )
    
    # Save image to buffer
    buf = BytesIO()
    image.save(buf, format="JPEG", quality=92)
    buf.seek(0)
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    r = requests.post(url, data={
        "chat_id": TELEGRAM_CHAT_ID,
        "caption": caption,
        "parse_mode": "Markdown"
    }, files={"photo": ("post.jpg", buf, "image/jpeg")}, timeout=30)
    
    if r.status_code == 200:
        print(f"✅ Sent to Telegram: {title[:60]}")
        return True
    else:
        print(f"❌ Telegram error: {r.text}")
        return False

# ── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*60}")
    print(f"🤖 Real Madrid Bot — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    sent = load_sent()
    
    # Fetch articles from all sources
    articles = fetch_rss_articles()
    articles += fetch_gnews_articles()
    
    # Deduplicate by link
    seen_links = set()
    unique = []
    for a in articles:
        if a["link"] not in seen_links:
            seen_links.add(a["link"])
            unique.append(a)
    
    print(f"📰 Found {len(unique)} Real Madrid articles")
    
    # Filter already sent
    new_articles = [a for a in unique if article_id(a["link"]) not in sent]
    print(f"🆕 {len(new_articles)} new articles to process")
    
    if not new_articles:
        print("No new articles. Exiting.")
        return
    
    # Process the LATEST article (most recent first, max 1 per run to avoid spam)
    article = new_articles[0]
    print(f"\n📰 Processing: {article['title'][:70]}")
    
    try:
        # Generate post image
        image = make_post_image(article)
        
        # Send to Telegram
        success = send_to_telegram(article, image)
        
        if success:
            sent.add(article_id(article["link"]))
            save_sent(sent)
    except Exception as e:
        print(f"❌ Error processing article: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
