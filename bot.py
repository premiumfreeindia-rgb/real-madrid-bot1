import os
import re
import time
import json
import hashlib
import requests
import textwrap
import threading
from datetime import datetime
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import feedparser
from flask import Flask

# ── FLASK WEB SERVER (required by Render free tier) ──────────────────────────
app = Flask(__name__)

@app.route("/")
def home():
    return "👑 Real Madrid Zone Bot is running!", 200

@app.route("/health")
def health():
    return {"status": "running", "bot": "Real Madrid Zone", "time": datetime.now().isoformat()}, 200

# ── CONFIG ────────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
SENT_FILE        = "/tmp/sent_articles.json"
INTERVAL_MINUTES = 30

RSS_FEEDS = [
    "https://feeds.feedburner.com/goal/realmadrid",
    "https://www.managingmadrid.com/rss/current",
    "https://realmadridnews.com/feed/",
    "https://www.101greatgoals.com/feed/category/real-madrid/",
    "https://feeds.feedburner.com/RealMadridLatestNews",
    "https://www.football-espana.net/feed",
    "https://www.madridistareal.net/feed",
]

GOLD    = (212, 175, 55)
WHITE   = (255, 255, 255)
BLACK   = (10, 10, 10)
DARK_BG = (15, 15, 20)

# ── HELPERS ───────────────────────────────────────────────────────────────────

def load_sent():
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE) as f:
            return set(json.load(f))
    return set()

def save_sent(sent):
    with open(SENT_FILE, "w") as f:
        json.dump(list(sent)[-200:], f)

def article_id(url):
    return hashlib.md5(url.encode()).hexdigest()

def clean_html(text):
    text = re.sub(r'<[^>]+>', '', text)
    return re.sub(r'\s+', ' ', text).strip()

# ── NEWS SCRAPING ─────────────────────────────────────────────────────────────

def fetch_rss_articles():
    articles = []
    keywords = [
        "real madrid", "realmadrid", "vinicius", "bellingham",
        "ancelotti", "mbappe", "mbappé", "bernabeu",
        "kroos", "modric", "courtois", "rodrygo", "valverde"
    ]
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0"})
            for entry in feed.entries[:5]:
                title   = entry.get("title", "")
                summary = entry.get("summary", "")
                link    = entry.get("link", "")
                if not any(kw in (title + summary).lower() for kw in keywords):
                    continue
                image_url = None
                if hasattr(entry, "media_content") and entry.media_content:
                    image_url = entry.media_content[0].get("url")
                elif hasattr(entry, "enclosures") and entry.enclosures:
                    image_url = entry.enclosures[0].get("href")
                if not image_url:
                    content = entry.get("content", [{}])[0].get("value", "") if entry.get("content") else ""
                    imgs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', content + summary)
                    if imgs:
                        image_url = imgs[0]
                articles.append({
                    "title":     title,
                    "summary":   clean_html(summary)[:300],
                    "link":      link,
                    "image_url": image_url,
                    "source":    feed.feed.get("title", url.split("/")[2]),
                })
        except Exception as e:
            print(f"RSS error {url}: {e}")
    return articles

def get_article_image(url):
    if not url:
        return None
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        return Image.open(BytesIO(r.content)).convert("RGBA")
    except:
        return None

# ── IMAGE GENERATION ──────────────────────────────────────────────────────────

def generate_anime_image(article):
    title  = article["title"]
    prompt = (
        f"anime style illustration, Real Madrid football fan art, "
        f"scene depicting: {title[:80]}, Santiago Bernabeu stadium, "
        f"dramatic lighting, gold and white color palette, "
        f"high quality anime art, cinematic composition, no text, detailed"
    )
    encoded  = requests.utils.quote(prompt)
    poll_url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=1080&height=1080&model=flux&nologo=true&seed={int(time.time())}"
    )
    print("🎨 Generating image via Pollinations...")
    try:
        r = requests.get(poll_url, timeout=90)
        if r.status_code == 200 and len(r.content) > 10000:
            img = Image.open(BytesIO(r.content)).convert("RGBA")
            print("✅ Image generated")
            return img
    except Exception as e:
        print(f"Pollinations error: {e}")

    if article.get("image_url"):
        img = get_article_image(article["image_url"])
        if img:
            print("✅ Using article image as fallback")
            return img

    print("⚠️ Using gradient fallback")
    img  = Image.new("RGBA", (1080, 1080), DARK_BG)
    draw = ImageDraw.Draw(img)
    for i in range(1080):
        draw.line([(0, i), (1080, i)], fill=(212, 175, 55, int(80 * (1 - i / 1080))))
    return img

def make_post_image(article):
    POST_W, POST_H = 1080, 1350
    bg     = generate_anime_image(article).convert("RGBA").resize((POST_W, POST_H), Image.LANCZOS)
    canvas = Image.new("RGBA", (POST_W, POST_H), DARK_BG)
    canvas.paste(bg, (0, 0))

    overlay = Image.new("RGBA", (POST_W, POST_H), (0, 0, 0, 0))
    ov      = ImageDraw.Draw(overlay)
    for i in range(280):
        ov.line([(0, i), (POST_W, i)], fill=(10, 10, 15, int(220 * (1 - i / 280))))
    for i in range(POST_H - 650, POST_H):
        ov.line([(0, i), (POST_W, i)], fill=(10, 10, 15, int(245 * ((i - (POST_H - 650)) / 650))))
    canvas = Image.alpha_composite(canvas, overlay)
    draw   = ImageDraw.Draw(canvas)

    def f(size, bold=False):
        for p in [
            f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
            f"/usr/share/fonts/truetype/liberation/LiberationSans-{'Bold' if bold else 'Regular'}.ttf",
        ]:
            if os.path.exists(p):
                try: return ImageFont.truetype(p, size)
                except: pass
        return ImageFont.load_default()

    fb, fs, fh, fbd, ft, ff = f(28,True), f(22), f(52,True), f(30), f(24,True), f(22)

    # Header
    draw.rectangle([(0,0),(POST_W,6)], fill=GOLD)
    draw.text((50,30), "⚽ REAL MADRID ZONE", font=fb, fill=GOLD)
    draw.text((50,68), f"📡 {article.get('source','Football News')[:30]}", font=fs, fill=(180,180,180))
    draw.text((POST_W-220,68), datetime.now().strftime("%b %d, %Y · %H:%M"), font=fs, fill=(150,150,150))
    draw.rectangle([(50,105),(POST_W-50,107)], fill=(212,175,55,180))

    cy = POST_H - 640
    tag = "  🏟 LATEST NEWS  "
    tw  = draw.textlength(tag, font=ft)
    draw.rounded_rectangle([(50,cy),(50+tw+10,cy+38)], radius=6, fill=GOLD)
    draw.text((55,cy+4), tag, font=ft, fill=BLACK)
    cy += 55

    # Headline
    words, lines, cur = article["title"].split(), [], ""
    for word in words:
        test = (cur + " " + word).strip()
        if draw.textlength(test, font=fh) < POST_W - 100:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = word
        if len(lines) >= 3: break
    if cur and len(lines) < 3: lines.append(cur)
    for i, line in enumerate(lines[:3]):
        draw.text((52, cy+i*65+2), line, font=fh, fill=(0,0,0,200))
        draw.text((50, cy+i*65),   line, font=fh, fill=WHITE)
    cy += len(lines)*65 + 20
    draw.rectangle([(50,cy),(POST_W//2,cy+3)], fill=GOLD)
    cy += 20

    # Summary
    for sent in [s.strip() for s in re.split(r'[.!?]+', article.get("summary","")) if len(s.strip())>20][:3]:
        if cy > POST_H - 200: break
        for j, wl in enumerate(textwrap.wrap(sent, width=42)[:2]):
            draw.text((50,cy), ("▸ " if j==0 else "   ")+wl, font=fbd, fill=(230,230,230))
            cy += 38
        cy += 5

    # Footer
    draw.rectangle([(0,POST_H-90),(POST_W,POST_H-88)], fill=(212,175,55,120))
    draw.text((50,POST_H-80), "#RealMadrid #HalaMadrid #UCL #LaLiga #RMCF", font=ff, fill=(180,180,180))
    crown = "👑 Real Madrid Zone"
    draw.text((POST_W-draw.textlength(crown,font=fb)-50, POST_H-115), crown, font=fb, fill=GOLD)
    draw.rectangle([(0,POST_H-6),(POST_W,POST_H)], fill=GOLD)

    return canvas.convert("RGB")

# ── TELEGRAM ──────────────────────────────────────────────────────────────────

def send_to_telegram(article, image):
    caption = (
        f"👑 *REAL MADRID ZONE*\n\n"
        f"🏟 *{article['title']}*\n\n"
        f"{article.get('summary','')[:300]}\n\n"
        f"📡 Source: {article.get('source','')}\n"
        f"🔗 [Read Full Article]({article.get('link','')})\n\n"
        f"#RealMadrid #HalaMadrid #UCL #LaLiga #RMCF"
    )
    buf = BytesIO()
    image.save(buf, format="JPEG", quality=92)
    buf.seek(0)
    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
        data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "Markdown"},
        files={"photo": ("post.jpg", buf, "image/jpeg")},
        timeout=30
    )
    if r.status_code == 200:
        print(f"✅ Sent: {article['title'][:60]}")
        return True
    print(f"❌ Telegram error: {r.text}")
    return False

# ── BOT MAIN ──────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*55}\n🤖 Real Madrid Bot — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'='*55}")
    sent     = load_sent()
    articles = fetch_rss_articles()

    seen, unique = set(), []
    for a in articles:
        if a["link"] not in seen:
            seen.add(a["link"])
            unique.append(a)

    new = [a for a in unique if article_id(a["link"]) not in sent]
    print(f"📰 {len(unique)} total | 🆕 {len(new)} new")
    if not new:
        print("No new articles.")
        return

    article = new[0]
    print(f"📰 Processing: {article['title'][:70]}")
    try:
        image = make_post_image(article)
        if send_to_telegram(article, image):
            sent.add(article_id(article["link"]))
            save_sent(sent)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback; traceback.print_exc()

def bot_loop():
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ TELEGRAM_TOKEN or TELEGRAM_CHAT_ID missing in environment!")
        return
    print("🤖 Bot background thread started")
    while True:
        try:
            main()
        except Exception as e:
            print(f"❌ Loop error: {e}")
        print(f"⏳ Sleeping {INTERVAL_MINUTES} min...\n")
        time.sleep(INTERVAL_MINUTES * 60)

# ── ENTRY POINT ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    threading.Thread(target=bot_loop, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Starting web server on port {port}")
    app.run(host="0.0.0.0", port=port)
