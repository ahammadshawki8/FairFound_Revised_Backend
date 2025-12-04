"""
API Views for Agentic AI Infrastructure
Provides endpoints for monitoring, learning, and managing the agent system.
"""
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone

from .registry import AgentRegistry
from .orchestrator import get_orchestrator, AgentContext
from .monitoring import get_monitor
from .memory import get_memory
from .adaptive import get_adaptive_agent
from .explainer import get_explainer
from .events import get_event_bus, EventTypes


class AgentRegistryView(APIView):
    """View registered agents and their status"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get all registered agents"""
        health_report = AgentRegistry.get_health_report()
        
        return Response({
            'agents': health_report['agents'],
            'summary': health_report['health_summary'],
            'total_agents': health_report['total_agents'],
            'enabled_agents': health_report['enabled_agents']
        })


class AgentHealthView(APIView):
    """Get health status for a specific agent"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, agent_id):
        """Get health status for an agent"""
        monitor = get_monitor()
        health = monitor.get_agent_health(agent_id)
        
        return Response(health)


class MonitoringDashboardView(APIView):
    """Get monitoring dashboard metrics"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get dashboard metrics"""
        monitor = get_monitor()
        metrics = monitor.get_dashboard_metrics()
        
        return Response(metrics)


class AlertsView(APIView):
    """View and manage alerts"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get alerts"""
        monitor = get_monitor()
        
        severity = request.query_params.get('severity')
        agent_id = request.query_params.get('agent_id')
        limit = int(request.query_params.get('limit', 50))
        
        from .monitoring import AlertSeverity
        severity_enum = None
        if severity:
            try:
                severity_enum = AlertSeverity(severity)
            except ValueError:
                pass
        
        alerts = monitor.get_alerts(severity_enum, agent_id, limit)
        
        return Response({
            'alerts': alerts,
            'total': len(alerts)
        })

    def delete(self, request):
        """Clear alerts"""
        monitor = get_monitor()
        agent_id = request.query_params.get('agent_id')
        
        monitor.clear_alerts(agent_id)
        
        return Response({'message': 'Alerts cleared'})


class AnomalyDetectionView(APIView):
    """Detect anomalies in agent behavior"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Detect current anomalies"""
        monitor = get_monitor()
        anomalies = monitor.detect_anomalies()
        
        return Response({
            'anomalies': anomalies,
            'total': len(anomalies),
            'checked_at': timezone.now().isoformat()
        })


class AgentMemoryView(APIView):
    """View and manage agent memory"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, agent_id=None):
        """Get agent accuracy and learning insights"""
        memory = get_memory()
        
        if agent_id:
            accuracy = memory.get_agent_accuracy(agent_id)
            insights = memory.get_learning_insights(agent_id)
            
            return Response({
                'agent_id': agent_id,
                'accuracy': accuracy,
                'learning_insights': insights
            })
        
        # Return summary for all agents
        from .models import AgentInteraction
        
        agent_ids = AgentInteraction.objects.values_list(
            'agent_id', flat=True
        ).distinct()
        
        summaries = {}
        for aid in agent_ids:
            summaries[aid] = memory.get_agent_accuracy(aid)
        
        return Response({
            'agents': summaries,
            'total_interactions': AgentInteraction.objects.count()
        })


class SimilarCasesView(APIView):
    """Find similar past cases"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Find similar cases for given context"""
        memory = get_memory()
        
        context = request.data.get('context', {})
        agent_id = request.data.get('agent_id')
        limit = request.data.get('limit', 5)
        
        similar = memory.retrieve_similar_cases(context, agent_id, limit)
        
        return Response({
            'similar_cases': similar,
            'total': len(similar)
        })


class AdaptiveLearningView(APIView):
    """Adaptive learning endpoints"""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        """Get learning summary and proposed weight updates"""
        adaptive = get_adaptive_agent()
        
        # Get learning summary
        summary = adaptive.get_learning_summary()
        
        # Get proposed weight updates
        from datetime import timedelta
        updates = adaptive.learn_from_human_reviews(timedelta(days=30))
        
        return Response({
            'summary': summary,
            'proposed_updates': [
                {
                    'component': u.component,
                    'current': u.current_weight,
                    'proposed': u.proposed_weight,
                    'change': u.change,
                    'reason': u.reason,
                    'confidence': u.confidence
                }
                for u in updates
            ]
        })

    def post(self, request):
        """Apply weight updates"""
        adaptive = get_adaptive_agent()
        
        # Get proposed updates
        from datetime import timedelta
        updates = adaptive.learn_from_human_reviews(timedelta(days=30))
        
        min_confidence = request.data.get('min_confidence', 0.5)
        
        # Apply updates
        new_weights = adaptive.apply_weight_updates(updates, min_confidence)
        
        # Store in database
        from .models import AgentWeightHistory
        AgentWeightHistory.objects.create(
            weights=new_weights,
            previous_weights=adaptive.current_weights,
            changes={'updates': [u.component for u in updates if u.confidence >= min_confidence]},
            trigger='manual_apply',
            reviews_analyzed=len(updates),
            confidence=min_confidence,
            applied_by=request.user
        )
        
        return Response({
            'message': 'Weights updated',
            'new_weights': new_weights
        })


class PersonalizationView(APIView):
    """Get personalized recommendations for a user"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get personalization for current user"""
        adaptive = get_adaptive_agent()
        
        personalization = adaptive.personalize_for_user(request.user.id)
        
        return Response(personalization)


class ScoreExplanationView(APIView):
    """Get detailed explanation of a score"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, job_id):
        """Get explanation for a job's score"""
        from .models import IngestionJob
        
        try:
            job = IngestionJob.objects.get(id=job_id, user=request.user)
        except IngestionJob.DoesNotExist:
            return Response(
                {'error': 'Job not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not job.result:
            return Response(
                {'error': 'No results available'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        explainer = get_explainer()
        
        score_result = job.result.get('score_result', {})
        benchmark = job.result.get('benchmark', {})
        
        explanation = explainer.explain_score(score_result, benchmark)
        
        return Response(explanation.to_dict())


class CounterfactualView(APIView):
    """Get counterfactual analysis (what-if scenarios)"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, job_id):
        """Get counterfactuals for a job"""
        from .models import IngestionJob
        
        try:
            job = IngestionJob.objects.get(id=job_id, user=request.user)
        except IngestionJob.DoesNotExist:
            return Response(
                {'error': 'Job not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not job.result:
            return Response(
                {'error': 'No results available'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        explainer = get_explainer()
        
        score_result = job.result.get('score_result', {})
        explanation = explainer.explain_score(score_result)
        
        return Response({
            'counterfactuals': explanation.counterfactuals,
            'current_score': score_result.get('overall_score', 0)
        })


class DecisionTreeView(APIView):
    """Get decision tree visualization data"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, job_id):
        """Get decision tree for a job"""
        from .models import IngestionJob
        
        try:
            job = IngestionJob.objects.get(id=job_id, user=request.user)
        except IngestionJob.DoesNotExist:
            return Response(
                {'error': 'Job not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not job.result:
            return Response(
                {'error': 'No results available'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        explainer = get_explainer()
        
        score_result = job.result.get('score_result', {})
        tree = explainer.generate_decision_tree(score_result)
        
        return Response(tree)


class EventHistoryView(APIView):
    """View event history"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get event history"""
        event_bus = get_event_bus()
        
        event_type = request.query_params.get('event_type')
        agent_id = request.query_params.get('agent_id')
        job_id = request.query_params.get('job_id')
        limit = int(request.query_params.get('limit', 100))
        
        job_id_int = int(job_id) if job_id else None
        
        events = event_bus.get_history(event_type, agent_id, job_id_int, limit)
        
        return Response({
            'events': [e.to_dict() for e in events],
            'total': len(events),
            'stats': event_bus.get_stats()
        })


class WeightHistoryView(APIView):
    """View weight change history"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get weight history"""
        from .models import AgentWeightHistory
        
        limit = int(request.query_params.get('limit', 10))
        
        history = AgentWeightHistory.objects.all()[:limit]
        
        return Response({
            'history': [
                {
                    'id': h.id,
                    'weights': h.weights,
                    'previous_weights': h.previous_weights,
                    'changes': h.changes,
                    'trigger': h.trigger,
                    'reviews_analyzed': h.reviews_analyzed,
                    'confidence': h.confidence,
                    'created_at': h.created_at.isoformat()
                }
                for h in history
            ],
            'total': AgentWeightHistory.objects.count()
        })


class MarketTrendsView(APIView):
    """Get market trend data for skills"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get skill market trends"""
        from .adaptive import MarketTrendAnalyzer
        
        analyzer = MarketTrendAnalyzer()
        
        skills = request.query_params.getlist('skills')
        
        trends = analyzer.get_skill_trends(skills if skills else None)
        emerging = analyzer.get_emerging_skills()
        
        return Response({
            'trends': trends,
            'emerging_skills': emerging
        })
