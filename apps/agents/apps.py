from django.apps import AppConfig


class AgentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.agents'
    
    def ready(self):
        """Initialize the agentic AI system on startup"""
        # Import and register all agents
        try:
            from .registered_agents import register_all_agents
            from .events import setup_default_handlers
            
            # Register all agents with the registry
            registered = register_all_agents()
            print(f"[AGENTS] Registered {len(registered)} agents: {registered}")
            
            # Set up default event handlers
            setup_default_handlers()
            print("[AGENTS] Event handlers configured")
            
        except Exception as e:
            print(f"[AGENTS] Warning: Agent initialization failed: {e}")
