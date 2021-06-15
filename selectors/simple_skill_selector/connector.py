import asyncio
from typing import Dict, Callable


class SkillSelectorConnector:

    async def send(self, payload: Dict, callback: Callable):
        skills_for_uttr = [
            "dff_bot_persona_skill"
        ]

        asyncio.create_task(callback(
            task_id=payload['task_id'],
            response=list(set(skills_for_uttr))
        ))
