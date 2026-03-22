"""Conflict Worker - Scrape CFR Global Conflict Tracker

Reuses existing conflict_service.py logic in Celery task.
"""

from config.celery_config import celery_app
from models.database import SessionLocal, Conflict
from services.conflict_service import get_conflict_service
from models.redis_client import RedisPubSub
import asyncio


@celery_app.task(name="tasks.conflict_worker.scrape_conflicts")
def scrape_conflicts():
    """Scrape conflicts from CFR and store in database (sync wrapper)"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(scrape_conflicts_async())
        return result
    finally:
        loop.close()


async def scrape_conflicts_async():
    """Async conflict scraping"""
    try:
        service = get_conflict_service()
        result = await service.get_conflicts(force_refresh=True)
        
        if not result.get("success"):
            return {"status": "error", "message": "Scraping failed"}
        
        conflicts_data = result.get("conflicts", [])
        
        # Store in database
        db = SessionLocal()
        db.query(Conflict).delete()
        
        for conflict_data in conflicts_data:
            conflict = Conflict(
                id=conflict_data["id"],
                name=conflict_data["name"],
                status=conflict_data["status"],
                impact=conflict_data["impact"],
                severity=conflict_data["severity"],
                description=conflict_data.get("description", ""),
                lat=conflict_data.get("coordinates", {}).get("lat"),
                lon=conflict_data.get("coordinates", {}).get("lng"),
                region=conflict_data.get("region", "")
            )
            db.add(conflict)
        
        db.commit()
        db.close()
        
        # Publish update notification
        pubsub = RedisPubSub(channel="flashpoint:conflicts")
        pubsub.publish({
            "type": "conflicts_updated",
            "count": len(conflicts_data)
        })
        
        print(f"✅ Conflicts: Updated {len(conflicts_data)} conflicts")
        return {"status": "success", "count": len(conflicts_data)}
        
    except Exception as e:
        print(f"❌ Conflict scraping error: {e}")
        return {"status": "error", "message": str(e)}
