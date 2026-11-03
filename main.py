
import os
import httpx
from fastapi import FastAPI, Request, HTTPException
from openai import AsyncOpenAI

app = FastAPI()

client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
WEBHOOK_SECRET = os.environ["TV_WEBHOOK_TOKEN"]
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


@app.get("/")
async def home():
    return {"status": "Ty's AI Trade Desk is running"}


@app.post("/webhook/{secret}")
async def tradingview_alert(secret: str, request: Request):
    if secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        alert = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    prompt = f"""
You are Ty's AI Trade Desk, an alert-only futures market assistant.

Review this TradingView alert:
{alert}

Give a concise analysis with:
- Market and direction
- ORB breakout quality
- VWAP and trend context, if provided
- Entry, stop and targets, if provided
- Risks or missing confirmations

Do not invent prices or indicators.
Do not guarantee a trade will work.
If information is missing, say so.
Do not tell the user to execute automatically.
"""

    try:
        response = await client.responses.create(
            model=MODEL,
            input=prompt
        )
        analysis = response.output_text
    except Exception as e:
        analysis = f"AI analysis unavailable: {str(e)[:300]}\n\nRaw alert: {alert}"

    message = (
        "📊 TY'S AI TRADE DESK\n\n"
        f"{analysis}\n\n"
        "⚠️ Alert only. Review before taking any trade."
    )

    telegram_url = (
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    )

    async with httpx.AsyncClient(timeout=20) as http:
        result = await http.post(
            telegram_url,
            json={"chat_id": CHAT_ID, "text": message}
        )

    if result.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail="Telegram delivery failed"
        )

    return {"status": "alert sent"}
