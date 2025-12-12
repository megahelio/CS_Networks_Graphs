from atproto import Client, models
from textblob import TextBlob
import pandas as pd
from datetime import datetime, timezone
import matplotlib.pyplot as plt
import time
import json
from itertools import combinations
import os
from dotenv import load_dotenv

# --- CONFIGURAZIONE ---
load_dotenv()
HANDLE = os.getenv("BLUESKY_HANDLE", "")
PASSWORD = os.getenv("BLUESKY_PASSWORD", "")
KEYWORDS = [

     "energy transition", "greenhouse effect",
    "biodiversity", "extreme weather events", "emissions", "global warming", "glaciers", "renewable energy", "fake news", 
    "catastrophe", "anthropic", "sustainable biofuels", "desertification",
    "deforestation", "clean energy", "sea level rise", "extinction"
]

LOCATION_KEYWORDS = ["firenze", "florence", "toscana", "italia", "italy"]
DATE_START = datetime(2023, 1, 1, tzinfo=timezone.utc)
DATE_END = datetime(2025, 11, 25, tzinfo=timezone.utc)
OUTPUT_FILE = "bluesky_posts_complex.csv"

# --- LOGIN ---
print("🔐 Connessione a Bluesky...")
client = Client()
client.login(HANDLE, PASSWORD)
print("✅ Accesso effettuato!")

# --- RACCOLTA DATI ---
records = []
for keyword in KEYWORDS:
    cursor = '0'
    while True:
        if cursor is None or int(cursor) > 1000:
            break
        print(f"\n🔍 Cerco post con parola chiave: {keyword}")
        try:
            params = models.AppBskyFeedSearchPosts.Params(q=keyword, limit=100, cursor=cursor)
            feed = client.app.bsky.feed.search_posts(params)
            cursor = json.loads(feed.json())["cursor"]
            posts = feed.posts or []
            print(f"   → trovati {len(posts)} risultati | arrivato a {cursor}")

            for post in posts:
                # --- Testo e autore ---
                text = getattr(post.record, "text", "")
                created_at = getattr(post.record, "created_at", "")
                author = post.author
                handle = getattr(author, "handle", "")
                display_name = getattr(author, "display_name", "") or ""
                description = getattr(author, "description", "") or ""

                # --- Filtro localizzazione (bio + display_name) con gestione None ---
                author_text = (description or "") + (display_name or "")
                location_match = True
                # any(
                #     loc in author_text.lower()
                #     for loc in LOCATION_KEYWORDS
                # )

                # --- Filtro per data ---
                if created_at:
                    try:
                        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00")).astimezone(timezone.utc)
                    except:
                        continue
                    if not (DATE_START <= dt <= DATE_END):
                        continue
                else:
                    continue

                # --- Analisi sentiment ---
                sentiment_score = TextBlob(text).sentiment.polarity
                sentiment_label = "positivo" if sentiment_score > 0.1 else "negativo" if sentiment_score < -0.1 else "neutro"

                # --- Determina se repost o originale ---
                tipo_post = "originale"
                testo_finale = text

                if hasattr(post, "post") and hasattr(post.post, "record"):
                    record_obj = post.post.record
                    if hasattr(record_obj, "embed") and hasattr(record_obj.embed, "record") and hasattr(record_obj.embed.record, "value"):
                        embed_value = record_obj.embed.record.value
                        if hasattr(embed_value, "text"):
                            tipo_post = "repost"
                            testo_finale = embed_value.text
                elif hasattr(post, "repost") and hasattr(post.repost, "record") and hasattr(post.repost.record, "text"):
                    tipo_post = "repost"
                    testo_finale = post.repost.record.text

                # --- Salvataggio solo se localizzazione corrisponde ---
                if location_match:
                    records.append({
                        "keyword": keyword,
                        "tipo": tipo_post,
                        "autore": display_name,
                        "handle": handle,
                        "bio": description,
                        "testo": testo_finale,
                        "data": dt.strftime("%Y-%m-%d") if dt else "",
                        "sentiment": sentiment_label,
                        "score": sentiment_score
                    })

            time.sleep(2)  # per non saturare le richieste

        except Exception as e:
            print(f"⚠️ Errore nella ricerca di '{keyword}': {e}")
            continue

# --- SALVATAGGIO CSV ---
if records:
    df = pd.DataFrame(records)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\n💾 Salvati {len(df)} post in '{OUTPUT_FILE}'")

    # --- Grafico del sentiment ---
    sentiment_counts = df["sentiment"].value_counts()
    sentiment_counts.plot(kind="bar", title="Distribuzione sentiment (post filtrati)")
    plt.xlabel("Sentiment")
    plt.ylabel("Conteggio")
    plt.show()

else:
    print("\n⚠️ Nessun post trovato con i criteri specificati.")

print(KEYWORDS)
# print(df["testo"][2000])

new_df = {"w1":[],"w2":[],"n":[]}
for kws in list(combinations(KEYWORDS, 2)):
    all_ks = None
    for kw in kws:
        if all_ks is None:
            all_ks = df.testo.str.contains(kw)
        else:
            all_ks = all_ks & df.testo.str.contains(kw)
    new_df["w1"].append(kws[0])
    new_df["w2"].append(kws[1])
    new_df["n"].append(all_ks.sum())
    print(kws, all_ks.sum())
pd.DataFrame(new_df).to_excel("grafo.xlsx")