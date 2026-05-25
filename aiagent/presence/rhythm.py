from __future__ import annotations

from datetime import datetime

from aiagent.presence.models import MoodState, PresenceState

def choose_presence_state(now:datetime,mood:MoodState) -> PresenceState:
    hour = now.hour

    if 2<= hour <6:
        return "sleepy"
    
    elif 6<= hour< 9:
        return "reading"
    
    elif 9<= hour< 12:
        return "focused"
    
    elif 12<= hour<14:
        return "resting"
    
    elif 14<= hour<18:
        return "working"
    
    elif 18<=hour<22:
        return "listening"
    
    elif 22 <= hour or hour < 2:
        if mood.fatigue > 0.55:
            return "sleepy"
        return "thinking"

    return "idle"

def update_mood_for_time(now:datetime, mood:MoodState) -> MoodState:
    hour = now.hour
    next_mood = mood.model_copy()

    if 2 <= hour < 6:
        next_mood.energy = max(0.18, next_mood.energy - 0.18)
        next_mood.fatigue = min(0.9, next_mood.fatigue + 0.25)

    elif 6 <= hour < 9:
        next_mood.energy = min(0.75, next_mood.energy + 0.08)
        next_mood.fatigue = max(0.15, next_mood.fatigue - 0.08)

    elif 18 <= hour < 22:
        next_mood.warmth = min(0.9, next_mood.warmth + 0.08)
        next_mood.curiosity = min(0.85, next_mood.curiosity + 0.04)

    elif 22 <= hour or hour < 2:
        next_mood.energy = max(0.25, next_mood.energy - 0.08)
        next_mood.fatigue = min(0.75, next_mood.fatigue + 0.12)
        next_mood.warmth = min(0.85, next_mood.warmth + 0.05)

    return next_mood


def mood_label(mood:MoodState) ->str:
    if mood.fatigue >0.7:
        return "sleepy"
    
    if mood.energy >0.72 and mood.curiosity >0.7:
        return "bright"
    
    if mood.warmth > 0.72:
        return "warm"
    
    if mood.valence <0.25:
        return "quiet"
    
    return "neutral"