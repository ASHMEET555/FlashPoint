"""Commodity Worker - Fetch commodity prices

Reuses existing commodity_service.py logic in Celery task.
"""

from config.celery_config import celery_app
from models.database import SessionLocal, Commodity
from services.commodity_service import get_commodity_service
from models.redis_client import RedisPubSub
import asyncio
from datetime import datetime


@celery_app.task(name="tasks.commodity_worker.fetch_commodities")
def fetch_commodities():
    """Fetch commodity prices and store in database (sync wrapper)"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(fetch_commodities_async())
        return result
    finally:
        loop.close()


async def fetch_commodities_async():
    """Async commodity fetching"""
    try:
        service = get_commodity_service()
        result = await service.fetch_prices()
        
        if not result.get("success"):
            return {"status": "error", "message": "Fetch failed"}
        
        prices = result.get("prices", {})
        
        # Store in database
        db = SessionLocal()
        
        for symbol, data in prices.items():
            commodity = Commodity(
                symbol=symbol,
                name=data.get("name", symbol),
                rate=float(data["rate"]),
                unit=data.get("unit", "USD"),
                timestamp=datetime.utcnow(),
                change_24h=data.get("change_24h", 0.0)
            )
            db.add(commodity)
        
        db.commit()
        db.close()
        
        # Publish update notification
        pubsub = RedisPubSub(channel="flashpoint:commodities")
        pubsub.publish({
            "type": "commodities_updated",
            "prices": prices
        })
        
        print(f"✅ Commodities: Updated {len(prices)} prices")
        return {"status": "success", "count": len(prices)}
        
    except Exception as e:
        print(f"❌ Commodity fetch error: {e}")
        return {"status": "error", "message": str(e)}
