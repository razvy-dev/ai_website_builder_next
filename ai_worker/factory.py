from abc import ABC, abstractmethod


class Factory(ABC):
    def __init__(self, provider, model, api_key):
        self.provider = provider
        self.model = model
        self.api_key = api_key

    @staticmethod
    def create(provider, model, api_key):
        """
        Factory method to create the appropriate AI provider instance.
        
        Args:
            provider (str): The provider name ('openai', 'claude', or 'gemini')
            model (str): The model identifier (e.g., 'gpt-4', 'claude-3-opus', 'gemini-pro')
            api_key (str): The API key for the provider
            
        Returns:
            Factory: An instance of the appropriate provider class
            
        Raises:
            ValueError: If the provider is not supported
        """
        from ai_worker.openai import OpenAI
        from ai_worker.claude import Claude
        from ai_worker.gemini import Gemini
        
        providers = {
            'openai': OpenAI,
            'claude': Claude,
            'gemini': Gemini
        }
        
        provider_lower = provider.lower()
        if provider_lower not in providers:
            raise ValueError(f"Unsupported provider: {provider}. Supported providers: {', '.join(providers.keys())}")
        
        return providers[provider_lower](model, api_key)

    @abstractmethod
    def design_sanity_schema_model(self, prompt, state):
        """Design sanity schema validation - accepts ComponentState with Figma data"""
        pass

    @abstractmethod
    def design_query_model(self, prompt, system_prompt=None):
        """Process design query"""
        pass

    @abstractmethod
    def design_typescript_type(self, prompt, context=None):
        """Generate TypeScript type definitions"""
        pass

    @abstractmethod
    def design_component_model(self, prompt, system_prompt=None, temperature=0.7):
        """Generate component code"""
        pass