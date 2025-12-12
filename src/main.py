import os
import time
import json
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from datetime import datetime, timezone
from itertools import combinations
from dotenv import load_dotenv
from atproto import Client, models
from textblob import TextBlob
from deep_translator import GoogleTranslator
from graph_metrics import GraphMetrics
# import base.code_BS as config

# --- CONFIGURATION ---
load_dotenv()
HANDLE = os.getenv("BLUESKY_HANDLE", "")
PASSWORD = os.getenv("BLUESKY_PASSWORD", "")
KEYWORDS_EN = [ 
    "green transition"
    , "greenhouse effect"
    , "loss of biodiversity"
    , "extreme weather events"
    , "CO2"
    , "emissions"
    , "global warming"
    , "melting glaciers"
    , "renewable energy"
    , "fake news"
    , "catastrophe"
    , "anthropic"
    , "sustainable biofuels"
    , "desertification"
    , "deforestation"
    , "clean energy"
    , "sea level rise"
    , "extinction"


    # Other candidates (commented out)
    # "anthropic",
    # "anthropogenic",    
    # "fossil fuels",
    # "climate catastrophe",

    # "climate change",
    # "climate crisis",
    # "climate denial",
    # "sustainability",
    # "net zero",
    # "COP29",
    # "IPCC",

    # "climate hoax",
    # "greenhouse gas",
    # "climate emergency",
    # "climate science",
    # "carbon footprint",
    # "climate action",
    # "extreme weather",
    # "deforestation",
    # "clean energy",
    # "solar power",
    # "wind power",
    # "eco-anxiety",
    # "COP28",
    # "Greta Thunberg",
    # "decarbonization",
    # "pollution",
    # "fridays for future"
    ]
LOCATIONS_IT = ["firenze", "florence", "toscana", "italia", "italy"]
DATE_START = datetime(2023, 1, 1, tzinfo=timezone.utc)
DATE_END = datetime(2025, 11, 25, tzinfo=timezone.utc)
OUTPUT_FILE = "bluesky_posts_complex.csv"

# --- LOGIN ---
print("🔐 Connessione a Bluesky...")
client = Client()
client.login(HANDLE, PASSWORD)
print("✅ Accesso effettuato!")


def clean_text(text):
    """Replaces double quotes with single quotes to prevent CSV issues."""
    if not text:
        return ""
    return text.replace('"', "'")

def translate_keywords(keywords, target_lang='it'):
    """Translates a list of keywords to the target language."""
    translator = GoogleTranslator(source='auto', target=target_lang)
    translated = []
    print(f"Translating {len(keywords)} keywords to {target_lang}...")
    for kw in keywords:
        try:
            trans = translator.translate(kw)
            translated.append(trans.lower())
            # time.sleep(0.2) # Rate limiting avoidance
        except Exception as e:
            print(f"Error translating {kw}: {e}")
            translated.append(kw.lower()) # Fallback
    return translated

def get_sentiment(text, language='en'):
    """Computes sentiment polarity. Translates to EN if necessary."""
    if not text:
        return "neutro", 0.0
    
    analysis_text = text
    if language != 'en':
        try:
            analysis_text = GoogleTranslator(source=language, target='en').translate(text)
        except Exception:
            pass # Fallback to original text

    score = TextBlob(analysis_text).sentiment.polarity
    label = "positivo" if score > 0.1 else "negativo" if score < -0.1 else "neutro"
    return label, score

def fetch_posts(client, keywords, location_filter=None, language_code='en', translate_content=False):
    """Fetches posts for given keywords and optional location filter."""
    records = []
    print(f"\n--- Starting Fetch for Language: {language_code.upper()} ---")
    
    for keyword in keywords:
        cursor = '0'
        count = 0
        while True:
            if cursor is None or (isinstance(cursor, int) and int(cursor) > 1000): # Safety break
                break
                
            print(f"[{language_code}] Searching '{keyword}' (cursor: {cursor})...")
            try:
                params = models.AppBskyFeedSearchPosts.Params(q=keyword, limit=50, cursor=cursor)
                feed = client.app.bsky.feed.search_posts(params)
                
                # Handle cursor safely
                if hasattr(feed, 'cursor') and feed.cursor:
                    cursor = feed.cursor
                else:
                    try:
                        cursor = json.loads(feed.json()).get("cursor")
                    except:
                        cursor = None

                posts = feed.posts or []
                print(f"   -> Found {len(posts)} posts. Processing...")

                for post in posts:
                    text = getattr(post.record, "text", "")
                    created_at = getattr(post.record, "created_at", "")
                    author = post.author
                    display_name = getattr(author, "display_name", "") or ""
                    description = getattr(author, "description", "") or ""
                    
                    # --- LOCATION FILTER ---
                    if location_filter:
                        author_text = (description or "") + (display_name or "")
                        if not any(loc in author_text.lower() for loc in location_filter):
                            continue

                    # --- DATE FILTER ---
                    if created_at:
                        try:
                            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00")).astimezone(timezone.utc)
                            if not (DATE_START <= dt <= DATE_END):
                                continue
                        except:
                            continue
                    else:
                        continue

                    # --- CLEAN TEXT ---
                    cleaned_text = clean_text(text)

                    # --- SENTIMENT ---
                    sent_lang = 'it' if translate_content else 'en'
                    # If we need to translate content for sentiment (IT -> EN)
                    sentiment_label, sentiment_score = get_sentiment(cleaned_text, language=sent_lang)

                    records.append({
                        "keyword": keyword,
                        "text": cleaned_text,
                        "author": display_name,
                        "date": dt.strftime("%Y-%m-%d"),
                        "sentiment": sentiment_label,
                        "score": sentiment_score,
                        "lang": language_code
                    })
                    count += 1
                
                if not cursor or count >= 50: # Limit per keyword for demo speed
                    break
                    
                time.sleep(1) # Polite delay

            except Exception as e:
                print(f"Error searching '{keyword}': {e}")
                break
    
    return records

def build_graph(records, all_keywords):
    """
    Builds a weighted Keyword Co-occurrence Graph.
    Nodes: Keywords (attribute 'count' = frequency in posts).
    Edges: Co-occurrences (weight = count of posts containing both).
    """
    G = nx.Graph()
    G.add_nodes_from(all_keywords)
    
    # Initialize node counts
    node_counts = {k: 0 for k in all_keywords}
    
    # Pre-process: group records by post text to identify unique posts and their keywords
    unique_posts_keywords = {} # txt -> set(keywords)
    
    for r in records:
        txt = r.get('text', '') or r.get('testo', '') # Safety fallback
        kw = r['keyword']
        if not txt: continue
        
        if txt not in unique_posts_keywords:
            unique_posts_keywords[txt] = set()
        unique_posts_keywords[txt].add(kw)

    # Build Graph
    # 1. Update Node Counts & 2. Add Edges
    for txt, kws_in_post in unique_posts_keywords.items():
        # Filter for only relevant keywords (safety)
        kws = [k for k in kws_in_post if k in all_keywords]
        
        # Update Node Counts
        for k in kws:
            node_counts[k] += 1
            
        # Update Edges (Co-occurrences)
        for u, v in combinations(kws, 2):
            if G.has_edge(u, v):
                G[u][v]['weight'] += 1
            else:
                G.add_edge(u, v, weight=1)
                
    # Set Node Attributes
    nx.set_node_attributes(G, node_counts, 'count')
    
    # Remove isolated nodes if desired? 
    # The requirement doesn't specify, but often visualisations are better without them.
    # Let's keep them as they are part of the "defined keywords" set.
                
    return G

def run_pipeline():
    
    # --- 1. PREPARE KEYWORDS ---
    print("\n--- Preparing Keywords ---")
    keywords_en = KEYWORDS_EN
    keywords_it = translate_keywords(keywords_en, 'it')
    
    # --- 2. EXECUTE PIPELINES ---
    
    # GLOBAL (EN)
    print("\n🚀 Starting GLOBAL (EN) Pipeline...")
    file_en = "../data/posts_en.csv"
    records_en = []
    fetch_en = True

    if os.path.exists(file_en):
        choice = input(f"⚠️ Il file '{file_en}' esiste già. Vuoi scaricare di nuovo i dati? (s/N): ").strip().lower()
        if choice != 's':
            fetch_en = False
            print(f"📂 Caricamento dati da '{file_en}'...")
            try:
                df_en = pd.read_csv(file_en)
                records_en = df_en.to_dict('records')
            except Exception as e:
                print(f"❌ Errore nel caricamento del file: {e}")
                fetch_en = True

    if fetch_en:
        print("🔐 Logging in...")
        client = Client()
        client.login(HANDLE, PASSWORD)
        print("✅ Logged in.")
        
        # Save keywords for reference
        pd.DataFrame({'en': keywords_en, 'it': keywords_it}).to_csv("../data/keywords_map.csv", index=False)
        
        records_en = fetch_posts(client, keywords_en, location_filter=None, language_code='en', translate_content=False)
        if records_en:
            df_en = pd.DataFrame(records_en)
            df_en.to_csv(file_en, index=False)
            print(f"💾 Saved {len(df_en)} English posts to {file_en}.")
    
    if records_en:
        G_en = build_graph(records_en, keywords_en)
        metrics_en = GraphMetrics(nx.to_numpy_array(G_en)) # GraphMetrics logic builds graph from array? 
        # Wait, GraphMetrics expects adjacency matrix IF we pass a list/array.
        # But we built a NetworkX graph 'G_en'.
        # We should update GraphMetrics to accept a NetworkX graph OR 
        # export adjacency matrix from G_en.
        # Let's pass the adj matrix as before to minimize changes to GraphMetrics __init__ logic
        # which rebuilds the graph. 
        # Ideally we should refactor GraphMetrics to take G directly, but sticking to plan:
        
        # The build_graph returns a NetworkX graph.
        # GraphMetrics takes an adjacency matrix and REBUILDS it.
        # Note: If we just pass `nx.to_numpy_array(G_en)`, we lose the Node Attributes ('count') we just added?
        # GraphMetrics doesn't seem to use 'count' attribute currently, so it's fine.
        # It calculates degrees itself.
        
        adj_matrix = nx.to_numpy_array(G_en)
        metrics_en = GraphMetrics(adj_matrix)
        
        report_en = metrics_en.report_all()
        
        # Save readable report
        with open("../data/report_en.json", "w") as f:
            json.dump(report_en, f, default=lambda x: str(x), indent=4)
            
        print("📊 Global Metrics Computed.")
        print("📈 Generating Plots...")
        metrics_en.plot_distributions("../data/plots_en")

    else:
        print("⚠️ No English posts found.")

    # ITALY (IT)
    print("\n🚀 Starting ITALY (IT) Pipeline...")
    file_it = "../data/posts_it.csv"
    records_it = []
    fetch_it = True

    if os.path.exists(file_it):
        choice = input(f"⚠️ Il file '{file_it}' esiste già. Vuoi scaricare di nuovo i dati? (s/N): ").strip().lower()
        if choice != 's':
            fetch_it = False
            print(f"📂 Caricamento dati da '{file_it}'...")
            try:
                df_it = pd.read_csv(file_it)
                records_it = df_it.to_dict('records')
            except Exception as e:
                print(f"❌ Errore nel caricamento del file: {e}")
                fetch_it = True

    if fetch_it:
        # Re-login if needed or reuse client if available... well, we created client inside the 'if fetch_en' block
        # If we skipped EN fetch, client might not exist.
        try:
            client.me # Check session
        except:
             print("🔐 Logging in (for IT)...")
             client = Client()
             client.login(HANDLE, PASSWORD)

        records_it = fetch_posts(client, keywords_it, location_filter=LOCATIONS_IT, language_code='it', translate_content=True)
        if records_it:
            df_it = pd.DataFrame(records_it)
            df_it.to_csv(file_it, index=False)
            print(f"💾 Saved {len(df_it)} Italian posts to {file_it}.")
            
    if records_it:
        G_it = build_graph(records_it, keywords_it)
        adj_matrix_it = nx.to_numpy_array(G_it)
        metrics_it = GraphMetrics(adj_matrix_it)
        
        report_it = metrics_it.report_all()
        
        with open("../data/report_it.json", "w") as f:
            json.dump(report_it, f, default=lambda x: str(x), indent=4)
            
        print("📊 Italy Metrics Computed.")
        print("📈 Generating Plots...")
        metrics_it.plot_distributions("../data/plots_it")
    else:
        print("⚠️ No Italian posts found.")

    print("\n✅ Pipeline Finished!")

if __name__ == "__main__":
    run_pipeline()
