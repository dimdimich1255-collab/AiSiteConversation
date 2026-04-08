"""
AI Conversion Booster - Final Production Version
FastAPI + OpenAI + Static Hosting
"""

import json
import re
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse # Для отдачи HTML
from pydantic import BaseModel
import httpx
from bs4 import BeautifulSoup
from openai import OpenAI

app = FastAPI(title="AI Conversion Booster API")

# Настройки CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Твой ключ OpenAI
OPENAI_KEY = "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" 
client = OpenAI(api_key=OPENAI_KEY)

class AnalyzeRequest(BaseModel):
    url: str
    tier: str = "free"

# --- ЭТОТ БЛОК ОТВЕЧАЕТ ЗА ТО, ЧТОБЫ САЙТ ОТКРЫВАЛСЯ ПО ССЫЛКЕ ---
@app.get("/")
async def read_index():
    # Эта команда говорит серверу: "Когда заходят на главную, покажи index.html"
    return FileResponse("index.html")

def scrape_website(url: str) -> dict:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"}
    try:
        with httpx.Client(headers=headers, timeout=20.0, follow_redirects=True) as h_client:
            response = h_client.get(url)
            response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to load site: {str(e)}")

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "aside", "svg"]):
        tag.decompose()

    headlines = [t.get_text(strip=True) for t in soup.find_all(["h1", "h2"]) if len(t.get_text(strip=True)) > 5][:5]
    ctas = [btn.get_text(strip=True) for btn in soup.find_all(["button", "a"]) if len(btn.get_text(strip=True)) > 2][:5]
    
    return {
        "url": url,
        "page_title": soup.find("title").get_text(strip=True) if soup.find("title") else "Unknown",
        "headlines": headlines,
        "ctas": ctas,
        "word_count": len(soup.get_text().split()),
    }

def analyze_with_ai(scraped_data: dict, tier: str) -> dict:
    prompt = f"""You are a CRO expert. Analyze website: {scraped_data['url']}
    Title: {scraped_data['page_title']}
    Headlines: {scraped_data['headlines']}
    CTAs: {scraped_data['ctas']}
    
    Return ONLY a valid JSON with these EXACT keys for my frontend:
    1. "money_leaks": list of objects with "rank" (1,2,3), "problem", "explanation", "estimated_loss", "severity" ("high" or "medium").
    2. "exact_fixes": object with "headline_rewrites" (list of objects with "before", "after", "reason") and "cta_rewrites" (list of objects with "before", "after", "reason") and "structure_improvements" (list of objects with "element", "action", "example").
    3. "conversion_potential": object with "current_estimate", "improved_estimate", "improvement", "revenue_impact".
    4. "psychological_analysis": object with "trust_score", "clarity_score", "urgency_score" (0-10), "trust_issues" (list), "clarity_issues" (list), "emotional_hooks_missing" (string), "missing_triggers" (list).
    
    Language: Use the site's language.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Error: {str(e)}")

@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    url = request.url.strip()
    if not url.startswith("http"): url = "https://" + url
    scraped = scrape_website(url)
    analysis = analyze_with_ai(scraped, request.tier)
    return {
        "url": url,
        "tier": request.tier,
        "scraped_meta": {
            "title": scraped["page_title"], 
            "word_count": scraped["word_count"],
            "headline_count": len(scraped["headlines"]),
            "cta_count": len(scraped["ctas"])
        },
        **analysis
    }

if __name__ == "__main__":
    import uvicorn
    import os
    # Для Render важно использовать порт из переменной окружения
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
