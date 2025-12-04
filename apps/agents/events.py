"""
Event Bus - Event-driven communication between agents
"""
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
from enum import Enum
import logging
import threading
import queue
import json

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class AgentEvent:
    """Event emitted by agents"""
    event_type: str
    agent_id: str
    job_id: Optional[int] = None
    data: Dict[str, Any] = field(default_factory=dict)
    priority: EventPriority = EventPriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'event_type': self.event_type,
            'agent_id': self.agent_id,
            'job_id': self.job_id,
            'data': self.data,
            'priority': self.priority.value,
            'timestamp': self.timestamp.isoformat(),
            'correlation_id': self.correlation_id
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())


# Standard event types
class EventTypes:
    # Pipeline events
    PIPELINE_STARTED = 'pipeline_started'
    PIPELINE_COMPLETED = 'pipeline_completed'
    PIPELINE_FAILED = 'pipeline_failed'
    
    # Agent events
    AGENT_STARTED = 'agent_started'
    AGENT_COMPLETED = 'agent_completed'
    AGENT_FAILED = 'agent_failed'
    AGENT_RETRY = 'agent_retry'
    
    # Scoring events
    SCORE_CALCULATED = 'score_calculated'
    LOW_CONFIDENCE = 'low_confidence'
    HIGH_CONFIDENCE = 'high_confidence'
    
    # Human review events
    REVIEW_REQUESTED = 'review_requested'
    REVIEW_COMPLETED = 'review_completed'
    REVIEW_APPROVED = 'review_approved'
    REVIEW_REJECTED = 'review_rejected'
    
    # Insight events
    INSIGHT_GENERATED = 'insight_generated'
    INSIGHTS_READY = 'insights_ready'
    
    # Learning events
    FEEDBACK_RECEIVED = 'feedback_received'
    WEIGHTS_UPDATED = 'weights_updated'
    
    # Monitoring events
    ANOMALY_DETECTED = 'anomaly_detected'
    PERFORMANCE_DEGRADED = 'performance_degraded'


@dataclass
class Subscription:
    """Subscription to an event type"""
    event_type: str
    handler: Callable[[AgentEvent], None]
    filter_fn: Optional[Callable[[AgentEvent], bool]] = None
    priority: EventPriority = EventPriority.NORMAL
    once: bool = False  # If True, unsubscribe after first call
    
    def matches(self, event: AgentEvent) -> bool:
        """Check if event matches this subscription"""
        if self.event_type != '*' and self.event_type != event.event_type:
            return False
        if self.filter_fn and not self.filter_fn(event):
            return False
        return True


class EventBus:
    """
    Central event bus for agent communication.
    
    Features:
    - Publish/subscribe pattern
    - Event filtering
    - Priority-based handling
    - Async event processing (optional)
    - Event history
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._subscriptions: Dict[str, List[Subscription]] = defaultdict(list)
        self._event_history: List[AgentEvent] = []
        self._max_history = 1000
        self._lock = threading.Lock()
        self._async_queue: Optional[queue.Queue] = None
        self._async_worker: Optional[threading.Thread] = None
        self._initialized = True
    
    def subscribe(self, event_type: str, handler: Callable[[AgentEvent], None],
                  filter_fn: Callable[[AgentEvent], bool] = None,
                  priority: EventPriority = EventPriority.NORMAL,
                  once: bool = False) -> str:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Event type to subscribe to ('*' for all events)
            handler: Callback function to handle the event
            filter_fn: Optional filter function
            priority: Handler priority
            once: If True, unsubscribe after first call
        
        Returns:
            Subscription ID
        """
        subscription = Subscription(
            event_type=event_type,
            handler=handler,
            filter_fn=filter_fn,
            priority=priority,
            once=once
        )
        
        with self._lock:
            self._subscriptions[event_type].append(subscription)
            # Sort by priority (higher first)
            self._subscriptions[event_type].sort(
                key=lambda s: s.priority.value, reverse=True
            )
        
        subscription_id = f"{event_type}_{id(subscription)}"
        logger.debug(f"Subscribed to {event_type}: {subscription_id}")
        
        return subscription_id
    
    def unsubscribe(self, event_type: str, handler: Callable):
        """Unsubscribe a handler from an event type"""
        with self._lock:
            self._subscriptions[event_type] = [
                s for s in self._subscriptions[event_type]
                if s.handler != handler
            ]
    
    def publish(self, event: AgentEvent):
        """
        Publish an event to all subscribers.
        
        Args:
            event: The event to publish
        """
        logger.debug(f"Publishing event: {event.event_type} from {event.agent_id}")
        
        # Store in history
        with self._lock:
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history = self._event_history[-self._max_history:]
        
        # Get matching subscriptions
        subscriptions_to_call = []
        subscriptions_to_remove = []
        
        with self._lock:
            # Check specific event type subscriptions
            for sub in self._subscriptions.get(event.event_type, []):
                if sub.matches(event):
                    subscriptions_to_call.append(sub)
                    if sub.once:
                        subscriptions_to_remove.append((event.event_type, sub))
            
            # Check wildcard subscriptions
            for sub in self._subscriptions.get('*', []):
                if sub.matches(event):
                    subscriptions_to_call.append(sub)
                    if sub.once:
                        subscriptions_to_remove.append(('*', sub))
        
        # Call handlers
        for sub in subscriptions_to_call:
            try:
                sub.handler(event)
            except Exception as e:
                logger.error(f"Event handler error for {event.event_type}: {e}")
        
        # Remove one-time subscriptions
        with self._lock:
            for event_type, sub in subscriptions_to_remove:
                if sub in self._subscriptions[event_type]:
                    self._subscriptions[event_type].remove(sub)
    
    def publish_async(self, event: AgentEvent):
        """Publish event asynchronously"""
        if self._async_queue is None:
            self._start_async_worker()
        self._async_queue.put(event)
    
    def _start_async_worker(self):
        """Start async event processing worker"""
        self._async_queue = queue.Queue()
        self._async_worker = threading.Thread(target=self._async_worker_loop, daemon=True)
        self._async_worker.start()
    
    def _async_worker_loop(self):
        """Worker loop for async event processing"""
        while True:
            try:
                event = self._async_queue.get(timeout=1.0)
                self.publish(event)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Async worker error: {e}")
    
    def get_history(self, event_type: str = None, 
                    agent_id: str = None,
                    job_id: int = None,
                    limit: int = 100) -> List[AgentEvent]:
        """Get event history with optional filters"""
        with self._lock:
            events = self._event_history.copy()
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if agent_id:
            events = [e for e in events if e.agent_id == agent_id]
        if job_id:
            events = [e for e in events if e.job_id == job_id]
        
        return events[-limit:]
    
    def clear_history(self):
        """Clear event history"""
        with self._lock:
            self._event_history = []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        with self._lock:
            event_counts = defaultdict(int)
            for event in self._event_history:
                event_counts[event.event_type] += 1
            
            return {
                'total_events': len(self._event_history),
                'subscription_count': sum(len(subs) for subs in self._subscriptions.values()),
                'event_types': dict(event_counts),
                'subscribed_types': list(self._subscriptions.keys())
            }


# Convenience functions
def get_event_bus() -> EventBus:
    """Get the global event bus instance"""
    return EventBus()


def emit(event_type: str, agent_id: str, job_id: int = None, 
         data: Dict = None, priority: EventPriority = EventPriority.NORMAL):
    """Convenience function to emit an event"""
    event = AgentEvent(
        event_type=event_type,
        agent_id=agent_id,
        job_id=job_id,
        data=data or {},
        priority=priority
    )
    get_event_bus().publish(event)


def on(event_type: str, filter_fn: Callable = None):
    """Decorator to subscribe a function to an event type"""
    def decorator(handler: Callable):
        get_event_bus().subscribe(event_type, handler, filter_fn)
        return handler
    return decorator


# Pre-configured event handlers
class EventHandlers:
    """Collection of common event handlers"""
    
    @staticmethod
    def log_all_events(event: AgentEvent):
        """Log all events"""
        logger.info(f"[EVENT] {event.event_type} from {event.agent_id}: {event.data}")
    
    @staticmethod
    def flag_low_confidence(event: AgentEvent):
        """Flag low confidence evaluations for review"""
        if event.event_type == EventTypes.SCORE_CALCULATED:
            confidence = event.data.get('confidence', 1.0)
            if confidence < 0.8:
                emit(
                    EventTypes.LOW_CONFIDENCE,
                    event.agent_id,
                    event.job_id,
                    {'confidence': confidence, 'original_event': event.to_dict()}
                )
    
    @staticmethod
    def request_human_review(event: AgentEvent):
        """Request human review for low confidence events"""
        if event.event_type == EventTypes.LOW_CONFIDENCE:
            emit(
                EventTypes.REVIEW_REQUESTED,
                'event_handler',
                event.job_id,
                {'reason': 'low_confidence', 'confidence': event.data.get('confidence')}
            )


def setup_default_handlers():
    """Set up default event handlers"""
    bus = get_event_bus()
    
    # Log all events in debug mode
    bus.subscribe('*', EventHandlers.log_all_events, priority=EventPriority.LOW)
    
    # Flag low confidence scores
    bus.subscribe(EventTypes.SCORE_CALCULATED, EventHandlers.flag_low_confidence)
    
    # Request human review for low confidence
    bus.subscribe(EventTypes.LOW_CONFIDENCE, EventHandlers.request_human_review)
