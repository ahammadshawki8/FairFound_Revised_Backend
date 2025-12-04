"""
Agent Monitoring - Performance tracking and anomaly detection
"""
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum
import statistics
import logging
import json

from django.utils import timezone
from django.db.models import Avg, Count, F, Q
from django.db.models.functions import TruncHour, TruncDay

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """System alert"""
    severity: AlertSeverity
    agent_id: str
    message: str
    metric: str
    current_value: float
    threshold: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            'severity': self.severity.value,
            'agent_id': self.agent_id,
            'message': self.message,
            'metric': self.metric,
            'current_value': self.current_value,
            'threshold': self.threshold,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class AgentMetrics:
    """Metrics for a single agent"""
    agent_id: str
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_execution_time: float = 0.0
    avg_execution_time: float = 0.0
    min_execution_time: float = float('inf')
    max_execution_time: float = 0.0
    avg_confidence: float = 0.0
    confidence_scores: List[float] = field(default_factory=list)
    error_types: Dict[str, int] = field(default_factory=dict)
    last_execution: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions
    
    @property
    def failure_rate(self) -> float:
        return 1.0 - self.success_rate
    
    def record_execution(self, success: bool, execution_time: float, 
                        confidence: float = 0.0, error: str = None):
        """Record a single execution"""
        self.total_executions += 1
        self.total_execution_time += execution_time
        self.last_execution = datetime.now()
        
        if success:
            self.successful_executions += 1
        else:
            self.failed_executions += 1
            if error:
                error_type = error.split(':')[0] if ':' in error else error[:50]
                self.error_types[error_type] = self.error_types.get(error_type, 0) + 1
        
        # Update timing stats
        self.avg_execution_time = self.total_execution_time / self.total_executions
        self.min_execution_time = min(self.min_execution_time, execution_time)
        self.max_execution_time = max(self.max_execution_time, execution_time)
        
        # Update confidence stats
        if confidence > 0:
            self.confidence_scores.append(confidence)
            self.avg_confidence = statistics.mean(self.confidence_scores[-100:])
    
    def to_dict(self) -> Dict:
        return {
            'agent_id': self.agent_id,
            'total_executions': self.total_executions,
            'successful_executions': self.successful_executions,
            'failed_executions': self.failed_executions,
            'success_rate': self.success_rate,
            'avg_execution_time': self.avg_execution_time,
            'min_execution_time': self.min_execution_time if self.min_execution_time != float('inf') else 0,
            'max_execution_time': self.max_execution_time,
            'avg_confidence': self.avg_confidence,
            'error_types': self.error_types,
            'last_execution': self.last_execution.isoformat() if self.last_execution else None
        }


class MonitoringAgent:
    """
    Monitors agent health and performance.
    
    Features:
    - Track execution metrics per agent
    - Detect anomalies in performance
    - Generate alerts for issues
    - Provide dashboard metrics
    - Track confidence score distributions
    """
    
    def __init__(self):
        self._metrics: Dict[str, AgentMetrics] = {}
        self._alerts: List[Alert] = []
        self._max_alerts = 1000
        
        # Thresholds for alerts
        self.thresholds = {
            'success_rate_warning': 0.90,
            'success_rate_critical': 0.75,
            'execution_time_warning': 5.0,  # seconds
            'execution_time_critical': 10.0,
            'confidence_warning': 0.7,
            'confidence_critical': 0.5,
        }
    
    def track_execution(self, agent_id: str, success: bool, 
                       execution_time: float, confidence: float = 0.0,
                       error: str = None):
        """
        Track an agent execution.
        
        Args:
            agent_id: The agent that executed
            success: Whether execution succeeded
            execution_time: Time taken in seconds
            confidence: Confidence score (0-1)
            error: Error message if failed
        """
        # Initialize metrics if needed
        if agent_id not in self._metrics:
            self._metrics[agent_id] = AgentMetrics(agent_id=agent_id)
        
        metrics = self._metrics[agent_id]
        metrics.record_execution(success, execution_time, confidence, error)
        
        # Store in database
        self._store_metric(agent_id, success, execution_time, confidence, error)
        
        # Check for anomalies
        self._check_anomalies(agent_id, metrics, execution_time, confidence)
        
        logger.debug(f"Tracked execution for {agent_id}: success={success}, time={execution_time:.3f}s")
    
    def _store_metric(self, agent_id: str, success: bool, execution_time: float,
                     confidence: float, error: str):
        """Store metric in database"""
        from .models import AgentMetric
        
        try:
            AgentMetric.objects.create(
                agent_id=agent_id,
                success=success,
                execution_time=execution_time,
                confidence=confidence,
                error=error[:500] if error else None
            )
        except Exception as e:
            logger.warning(f"Failed to store metric: {e}")
    
    def _check_anomalies(self, agent_id: str, metrics: AgentMetrics,
                        execution_time: float, confidence: float):
        """Check for anomalies and generate alerts"""
        
        # Check success rate
        if metrics.total_executions >= 10:
            if metrics.success_rate < self.thresholds['success_rate_critical']:
                self._add_alert(Alert(
                    severity=AlertSeverity.CRITICAL,
                    agent_id=agent_id,
                    message=f"Critical: Success rate dropped to {metrics.success_rate:.1%}",
                    metric='success_rate',
                    current_value=metrics.success_rate,
                    threshold=self.thresholds['success_rate_critical']
                ))
            elif metrics.success_rate < self.thresholds['success_rate_warning']:
                self._add_alert(Alert(
                    severity=AlertSeverity.WARNING,
                    agent_id=agent_id,
                    message=f"Warning: Success rate at {metrics.success_rate:.1%}",
                    metric='success_rate',
                    current_value=metrics.success_rate,
                    threshold=self.thresholds['success_rate_warning']
                ))
        
        # Check execution time
        if execution_time > self.thresholds['execution_time_critical']:
            self._add_alert(Alert(
                severity=AlertSeverity.ERROR,
                agent_id=agent_id,
                message=f"Slow execution: {execution_time:.2f}s",
                metric='execution_time',
                current_value=execution_time,
                threshold=self.thresholds['execution_time_critical']
            ))
        elif execution_time > self.thresholds['execution_time_warning']:
            self._add_alert(Alert(
                severity=AlertSeverity.WARNING,
                agent_id=agent_id,
                message=f"Execution time elevated: {execution_time:.2f}s",
                metric='execution_time',
                current_value=execution_time,
                threshold=self.thresholds['execution_time_warning']
            ))
        
        # Check confidence
        if confidence > 0 and confidence < self.thresholds['confidence_critical']:
            self._add_alert(Alert(
                severity=AlertSeverity.WARNING,
                agent_id=agent_id,
                message=f"Low confidence score: {confidence:.2f}",
                metric='confidence',
                current_value=confidence,
                threshold=self.thresholds['confidence_critical']
            ))
    
    def _add_alert(self, alert: Alert):
        """Add an alert to the list"""
        self._alerts.append(alert)
        if len(self._alerts) > self._max_alerts:
            self._alerts = self._alerts[-self._max_alerts:]
        
        # Log the alert
        log_method = {
            AlertSeverity.INFO: logger.info,
            AlertSeverity.WARNING: logger.warning,
            AlertSeverity.ERROR: logger.error,
            AlertSeverity.CRITICAL: logger.critical
        }.get(alert.severity, logger.info)
        
        log_method(f"[ALERT] {alert.agent_id}: {alert.message}")
    
    def detect_anomalies(self) -> List[Dict]:
        """
        Detect anomalies across all agents.
        
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        for agent_id, metrics in self._metrics.items():
            # Check for sudden performance drops
            if metrics.total_executions >= 20:
                recent_success = self._get_recent_success_rate(agent_id, hours=1)
                historical_success = metrics.success_rate
                
                if recent_success < historical_success * 0.8:
                    anomalies.append({
                        'type': 'performance_drop',
                        'agent_id': agent_id,
                        'message': f"Recent success rate ({recent_success:.1%}) significantly lower than historical ({historical_success:.1%})",
                        'severity': 'warning'
                    })
            
            # Check for execution time spikes
            if metrics.avg_execution_time > 0:
                recent_avg = self._get_recent_avg_time(agent_id, hours=1)
                if recent_avg > metrics.avg_execution_time * 2:
                    anomalies.append({
                        'type': 'latency_spike',
                        'agent_id': agent_id,
                        'message': f"Recent avg time ({recent_avg:.2f}s) is 2x historical ({metrics.avg_execution_time:.2f}s)",
                        'severity': 'warning'
                    })
            
            # Check for confidence drift
            if len(metrics.confidence_scores) >= 20:
                recent_conf = statistics.mean(metrics.confidence_scores[-10:])
                historical_conf = statistics.mean(metrics.confidence_scores[:-10])
                
                if recent_conf < historical_conf * 0.85:
                    anomalies.append({
                        'type': 'confidence_drift',
                        'agent_id': agent_id,
                        'message': f"Confidence dropping: {recent_conf:.2f} vs {historical_conf:.2f}",
                        'severity': 'info'
                    })
        
        return anomalies
    
    def _get_recent_success_rate(self, agent_id: str, hours: int = 1) -> float:
        """Get success rate for recent period"""
        from .models import AgentMetric
        
        cutoff = timezone.now() - timedelta(hours=hours)
        recent = AgentMetric.objects.filter(
            agent_id=agent_id,
            created_at__gte=cutoff
        )
        
        total = recent.count()
        if total == 0:
            return self._metrics.get(agent_id, AgentMetrics(agent_id)).success_rate
        
        successful = recent.filter(success=True).count()
        return successful / total
    
    def _get_recent_avg_time(self, agent_id: str, hours: int = 1) -> float:
        """Get average execution time for recent period"""
        from .models import AgentMetric
        
        cutoff = timezone.now() - timedelta(hours=hours)
        result = AgentMetric.objects.filter(
            agent_id=agent_id,
            created_at__gte=cutoff
        ).aggregate(avg_time=Avg('execution_time'))
        
        return result['avg_time'] or 0.0
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """
        Get metrics for monitoring dashboard.
        
        Returns:
            Dictionary with dashboard data
        """
        from .models import AgentMetric
        
        # Overall stats
        total_executions = sum(m.total_executions for m in self._metrics.values())
        total_successful = sum(m.successful_executions for m in self._metrics.values())
        
        # Recent alerts
        recent_alerts = [a.to_dict() for a in self._alerts[-20:]]
        
        # Per-agent metrics
        agent_metrics = {
            agent_id: metrics.to_dict()
            for agent_id, metrics in self._metrics.items()
        }
        
        # Time series data (last 24 hours)
        time_series = self._get_time_series_data(hours=24)
        
        # Anomalies
        anomalies = self.detect_anomalies()
        
        return {
            'summary': {
                'total_executions': total_executions,
                'total_successful': total_successful,
                'overall_success_rate': total_successful / max(total_executions, 1),
                'active_agents': len(self._metrics),
                'alert_count': len(recent_alerts)
            },
            'agents': agent_metrics,
            'alerts': recent_alerts,
            'anomalies': anomalies,
            'time_series': time_series,
            'generated_at': datetime.now().isoformat()
        }
    
    def _get_time_series_data(self, hours: int = 24) -> Dict[str, List]:
        """Get time series data for charts"""
        from .models import AgentMetric
        
        cutoff = timezone.now() - timedelta(hours=hours)
        
        # Aggregate by hour
        hourly_data = AgentMetric.objects.filter(
            created_at__gte=cutoff
        ).annotate(
            hour=TruncHour('created_at')
        ).values('hour').annotate(
            total=Count('id'),
            successful=Count('id', filter=Q(success=True)),
            avg_time=Avg('execution_time'),
            avg_confidence=Avg('confidence')
        ).order_by('hour')
        
        return {
            'labels': [d['hour'].isoformat() for d in hourly_data],
            'executions': [d['total'] for d in hourly_data],
            'success_rate': [d['successful'] / max(d['total'], 1) for d in hourly_data],
            'avg_time': [d['avg_time'] or 0 for d in hourly_data],
            'avg_confidence': [d['avg_confidence'] or 0 for d in hourly_data]
        }
    
    def get_agent_health(self, agent_id: str) -> Dict[str, Any]:
        """Get health status for a specific agent"""
        metrics = self._metrics.get(agent_id)
        
        if not metrics:
            return {'status': 'unknown', 'message': 'No data available'}
        
        # Determine health status
        if metrics.success_rate >= 0.95 and metrics.avg_confidence >= 0.8:
            status = 'healthy'
            color = 'green'
        elif metrics.success_rate >= 0.80 and metrics.avg_confidence >= 0.6:
            status = 'degraded'
            color = 'yellow'
        else:
            status = 'unhealthy'
            color = 'red'
        
        return {
            'status': status,
            'color': color,
            'metrics': metrics.to_dict(),
            'recent_alerts': [
                a.to_dict() for a in self._alerts
                if a.agent_id == agent_id
            ][-5:]
        }
    
    def get_alerts(self, severity: AlertSeverity = None, 
                  agent_id: str = None,
                  limit: int = 50) -> List[Dict]:
        """Get alerts with optional filters"""
        alerts = self._alerts.copy()
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if agent_id:
            alerts = [a for a in alerts if a.agent_id == agent_id]
        
        return [a.to_dict() for a in alerts[-limit:]]
    
    def clear_alerts(self, agent_id: str = None):
        """Clear alerts"""
        if agent_id:
            self._alerts = [a for a in self._alerts if a.agent_id != agent_id]
        else:
            self._alerts = []


# Global monitoring instance
_monitor: Optional[MonitoringAgent] = None


def get_monitor() -> MonitoringAgent:
    """Get the global monitoring instance"""
    global _monitor
    if _monitor is None:
        _monitor = MonitoringAgent()
    return _monitor
