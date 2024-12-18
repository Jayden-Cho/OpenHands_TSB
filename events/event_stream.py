from core.logger import Logger
from typing import List, Union, Optional, Dict
from datetime import datetime
from events.action import Action
from events.observation import Observation

logger = Logger.get_logger()

class Event:
    def __init__(self, 
                 event_type: str, 
                 content: Union[Action, Observation],
                 metadata: Optional[Dict] = None):
        self.event_type = event_type
        self.content = content
        self.timestamp = datetime.now()
        self.metadata = metadata or {}

    def __str__(self) -> str:
        return f"[{self.timestamp}] {self.event_type}: {self.content}"

class EventStream:
    def __init__(self):
        self.events: List[Event] = []
        self._event_counter: Dict[str, int] = {}  # Track event counts by type
        
    def add_event(self, event: Event) -> None:
        """Add new event to the stream"""
        self.events.append(event)
        self._event_counter[event.event_type] = self._event_counter.get(event.event_type, 0) + 1
        logger.debug(f"New event added: {event}")
        
    def get_events(self, 
                  event_type: Optional[str] = None, 
                  start_time: Optional[datetime] = None,
                  end_time: Optional[datetime] = None) -> List[Event]:
        """Get events with optional filtering"""
        filtered_events = self.events

        if event_type:
            filtered_events = [e for e in filtered_events if e.event_type == event_type]
            
        if start_time:
            filtered_events = [e for e in filtered_events if e.timestamp >= start_time]
            
        if end_time:
            filtered_events = [e for e in filtered_events if e.timestamp <= end_time]
            
        return filtered_events
    
    def get_latest_event(self, event_type: Optional[str] = None) -> Optional[Event]:
        """Get most recent event of specified type"""
        events = self.get_events(event_type)
        return events[-1] if events else None
    
    def get_event_count(self, event_type: Optional[str] = None) -> int:
        """Get count of events by type"""
        if event_type:
            return self._event_counter.get(event_type, 0)
        return len(self.events)

    def clear(self) -> None:
        """Clear all events"""
        self.events.clear()
        self._event_counter.clear()