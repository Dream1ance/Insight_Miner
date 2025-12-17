import spacy
import pandas as pd
import joblib
import re
import requests
from bs4 import BeautifulSoup
from collections import Counter
import logging

# --- Model Loading (Load once at startup) ---
print("Loading NLP models... This may take a moment.")

try:
    # Prefer the large model but fall back to the small model to reduce size
    try:
        nlp = spacy.load("en_core_web_lg")
        print("Spacy 'en_core_web_lg' loaded.")
    except OSError:
        nlp = spacy.load("en_core_web_sm")
        print("Spacy 'en_core_web_sm' loaded as fallback.")
except Exception as e:
    print(f"Spacy model could not be loaded: {e}")
    nlp = None

try:
    classifier = joblib.load("article_classifier.pkl")
    print("Sentiment model 'article_classifier.pkl' loaded successfully.")
except FileNotFoundError:
    print("FATAL ERROR: 'article_classifier.pkl' not found.")
    print("Please make sure you have placed your trained .pkl file in this directory.")
    exit()
except Exception as e:
    print(f"Error loading article_classifier.pkl: {e}")
    exit()

# --- Financial Metrics Dictionary ---
FINANCIAL_METRICS = {
    'Revenue': {'keywords': ['revenue', 'sales'], 'pattern': r'\$[\d\.,]+\s*(?:billion|million|trillion)?'},
    'Net Income': {'keywords': ['net income'], 'pattern': r'\$[\d\.,]+\s*(?:billion|million|trillion)?'},
    'Operating Income': {'keywords': ['operating income'], 'pattern': r'\$[\d\.,]+\s*(?:billion|million|trillion)?'},
    'Earnings Per Share': {'keywords': ['earnings per share', 'diluted earnings per share'], 'pattern': r'\$[ \d\.,]+'}
}

# --- Web Scraping Functions ---

# NOTE: Google search scraping removed to reduce external scraping logic
# If you need search-as-query behavior, re-add a small wrapper or use an API.

def get_article_text(url: str) -> dict:
    """
    Fetches, parses, and cleans the text content and HEADING of a news article.
    Returns a dictionary: {'text': ..., 'heading': ...}
    """
    print(f"Scraping article from: {url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Extract Heading
        heading = "Article Report" # Default heading
        if soup.find('h1'):
            heading = soup.find('h1').get_text(strip=True)
        
        main_content = soup.find('article') or soup.find('main') or soup.body
        
        if main_content:
            for element in main_content(['script', 'style', 'header', 'footer', 'nav', 'aside', 'form', 'table']):
                element.decompose()
            text = main_content.get_text(separator=' ', strip=True)
        else:
            text = soup.get_text(separator=' ', strip=True)
            
        full_text = re.sub(r'\s+', ' ', text).strip()
        print(f"Successfully scraped {len(full_text)} characters.")
        
        return {'text': full_text, 'heading': heading}
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
        return {'text': f"Error: Could not retrieve article. {e}", 'heading': 'Scrape Failed'}
    except Exception as e:
        print(f"Error parsing content from {url}: {e}")
        return {'text': f"Error: Could not parse article. {e}", 'heading': 'Parse Failed'}


# --- Analysis Functions ---

def _heuristic_contextual_linker(doc: spacy.tokens.Doc) -> pd.DataFrame:
    """
    Custom algorithm to find and link financial facts in the text.
    """
    facts = []
    current_org = None
    
    for sent in doc.sents:
        sent_orgs = [ent.text for ent in sent.ents if ent.label_ == 'ORG']
        
        if sent_orgs:
            known_orgs = [org for org in sent_orgs if any(k in org for k in ['Microsoft', 'Apple', 'Google', 'Amazon'])]
            current_org = known_orgs[0] if known_orgs else sent_orgs[0]
        
        if not current_org:
            continue
            
        for metric_name, details in FINANCIAL_METRICS.items():
            if any(keyword in sent.text.lower() for keyword in details['keywords']):
                for value in re.findall(details['pattern'], sent.text, re.IGNORECASE):
                    if len(value) > 2:
                        facts.append({"Company": current_org, "Metric": metric_name, "Value": value.strip()})
                        
    if not facts:
        return pd.DataFrame(columns=["Company", "Metric", "Value"])
        
    return pd.DataFrame(facts).drop_duplicates().reset_index(drop=True)

def run_analysis(text: str) -> dict:
    """
    Main orchestration function. Takes raw text as input.
    """
    if not text or text.startswith("Error:") or len(text) < 150:
        print("Analysis skipped: Not enough text provided.")
        return {
            'summary': 'N/A - Could not process article text.',
            'entities': {},
            'article_type': 'N/A', 
            'financial_facts': pd.DataFrame(columns=['Company', 'Metric', 'Value']),
            'raw_text': text[:500] + "..." if text else "N/A"
        }
    # Simple lightweight summarization: use spaCy sentence segmentation
    print("--- Generating lightweight summary ---")
    try:
        MAX_CHARS = 40000
        text_clean = (text or "").strip()
        text_to_summarize = text_clean[:MAX_CHARS]

        if nlp is None:
            raise RuntimeError("spaCy model not available for summarization.")

        doc = nlp(text_to_summarize)
        # take the first 2-3 sentences as a simple summary
        summary_sentences = []
        for i, sent in enumerate(doc.sents):
            if i >= 3:
                break
            summary_sentences.append(sent.text.strip())

        summary = ' '.join(summary_sentences) if summary_sentences else (text_to_summarize[:300] + '...')
    except Exception as e:
        print(f"Error during lightweight summarization: {e}")
        summary = "Could not generate summary."

    print("--- Extracting entities and facts ---")
    doc = nlp(text[:50000]) if nlp is not None else None
    
    entities = {}
    if doc is not None:
        for label in ['ORG', 'PERSON', 'GPE']:
            label_entities = [ent.text.strip() for ent in doc.ents if ent.label_ == label]
            if label_entities:
                common_entities = [item.replace("\n", " ") for item, count in Counter(label_entities).most_common(5)]
                entities[label] = common_entities
            else:
                entities[label] = []
    else:
        entities = {'ORG': [], 'PERSON': [], 'GPE': []}

    print("--- Classifying sentiment ---")
    try:
        text_for_classification = " ".join(text.split()[:200])
        article_type = classifier.predict([text_for_classification])[0]
    except Exception as e:
        print(f"Error during classification: {e}")
        article_type = "Classification Failed"

    financial_facts_df = _heuristic_contextual_linker(doc)

    print("--- Analysis complete for one article ---")
    return {
        'summary': summary,
        'entities': entities,
        'article_type': article_type,
        'financial_facts': financial_facts_df,
    }