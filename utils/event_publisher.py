import json
import logging
from datetime import datetime
import uuid

logger = logging.getLogger("progress-service")


async def publish_event(redis_client, channel: str, event_data: dict, correlation_id: str = None):
    """Publish an event to Redis"""
    try:
        event = {
            "event": channel,
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "data": event_data
        }

        await redis_client.publish(channel, json.dumps(event))
        logger.info(f"Event published: {channel}", extra={"correlation_id": event["correlation_id"]})

        return event["correlation_id"]
    except Exception as e:
        logger.error(f"Failed to publish event to {channel}: {e}")


async def publish_achievement_earned(redis_client, achievement_data: dict, correlation_id: str = None):
    """Publish achievement.earned event"""
    return await publish_event(redis_client, "achievement.earned", {
        "achievement_id": str(achievement_data["id"]),
        "client_id": str(achievement_data["client_id"]),
        "type": achievement_data["achievement_type"],
        "title": achievement_data["title"],
        "description": achievement_data.get("description", ""),
        "badge_icon": achievement_data.get("badge_icon", "")
    }, correlation_id)


async def publish_milestone_reached(redis_client, milestone_data: dict, correlation_id: str = None):
    """Publish milestone.reached event"""
    return await publish_event(redis_client, "milestone.reached", milestone_data, correlation_id)


async def publish_progress_updated(redis_client, progress_data: dict, correlation_id: str = None):
    """Publish progress.updated event"""
    return await publish_event(redis_client, "progress.updated", progress_data, correlation_id)
