"""
AI Conversion Booster - Backend API (Final Optimized Version)
FastAPI + BeautifulSoup + OpenAI GPT-4o-mini
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from bs4 import BeautifulSoup
from openai import OpenAI
import json
import re
from typing import Optional

app = FastAPI(title="AI Conversion Booster API", version="1.0.3")

# Разрешаем фронтенду общаться с бэкендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Твой ключ OpenAI (уже на месте)
OPENAI_KEY = "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" 
client = OpenAI(api_key=OPENAI_KEY)

class AnalyzeRequest(BaseModel):
    url: str
    tier: str = "free"

def scrape_website(url: str) -> dict:
    """Скрапер для сбора данных с сайта"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    }
    try:
        with httpx.Client(headers=headers, timeout=20.0, follow_redirects=True) as h_client:
            response = h_client.get(url)
            response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Не удалось загрузить сайт: {str(e)}")

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "aside", "svg"]):
        tag.decompose()

    headlines = [t.get_text(strip=True) for t in soup.find_all(["h1", "h2"]) if len(t.get_text(strip=True)) > 5][:5]
    ctas = [btn.get_text(strip=True) for btn in soup.find_all(["button", "a"]) if len(btn.get_text(strip=True)) > 2][:5]
    
    return {
        "url": url,
        "page_title": soup.find("title").get_text(strip=True) if soup.find("title") else "Unknown Site",
        "headlines": headlines,
        "ctas": ctas,
        "word_count": len(soup.get_text().split()),
    }

def analyze_with_ai(scraped_data: dict, tier: str) -> dict:
    """Анализ через GPT-4o-mini с ключами, СТРОГО под твой JavaScript"""
    
    prompt = f"""You are a CRO expert. Analyze this website: {scraped_data['url']}
    Title: {scraped_data['page_title']}
    Headlines Found: {scraped_data['headlines']}
    CTAs Found: {scraped_data['ctas']}
    
    Return ONLY a valid JSON with these EXACT keys for my frontend:
    1. "money_leaks": list of objects with "rank" (1,2,3), "problem", "explanation", "estimated_loss", "severity" ("high" or "medium").
    2. "exact_fixes": object with "headline_rewrites" (list of objects with "before", "after", "reason") and "cta_rewrites" (list of objects with "before", "after", "reason") and "structure_improvements" (list of objects with "element", "action", "example").
    3. "conversion_potential": object with "current_estimate", "improved_estimate", "improvement", "revenue_impact".
    4. "psychological_analysis": object with "trust_score", "clarity_score", "urgency_score" (0-10), "trust_issues" (list), "clarity_issues" (list), "emotional_hooks_missing" (string), "missing_triggers" (list).
    
    Language: Use the language of the website for analysis text.
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
    # Передаем tier в функцию анализа
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
    uvicorn.run(app, host="127.0.0.1", port=8000)