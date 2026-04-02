from openai import OpenAI as OpenAIClient
from ai_worker.factory import Factory
import base64
import os
from pathlib import Path


class OpenAI(Factory):
    """OpenAI provider implementation"""
    
    def __init__(self, model, api_key):
        super().__init__("openai", model, api_key)
        self.client = OpenAIClient(api_key=api_key)
    
    def _make_request(self, messages, response_format=None, temperature=0.7):
        """Make API request to OpenAI"""
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        
        if response_format:
            params["response_format"] = response_format
        
        response = self.client.chat.completions.create(**params)
        return response.choices[0].message.content
    
    def _encode_image_to_base64(self, image_path):
        """Convert image file path to base64 data URL"""
        try:
            # Check if it's already a data URL
            if isinstance(image_path, str) and image_path.startswith('data:'):
                return image_path
            
            # Handle file paths
            if os.path.isfile(image_path):
                with open(image_path, 'rb') as image_file:
                    image_data = image_file.read()
                    base64_image = base64.b64encode(image_data).decode('utf-8')
                    
                    # Detect MIME type from extension
                    ext = Path(image_path).suffix.lower()
                    mime_types = {
                        '.png': 'image/png',
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.gif': 'image/gif',
                        '.webp': 'image/webp'
                    }
                    mime_type = mime_types.get(ext, 'image/png')
                    
                    return f"data:{mime_type};base64,{base64_image}"
            
            # If it's a URL, return None (will skip image)
            return None
        except Exception as e:
            print(f"Warning: Could not encode image {image_path}: {e}")
            return None
    
    def design_sanity_schema_model(self, prompt, state):
        """Design sanity schema validation"""
        # Truncate raw_node_json to prevent token overflow (max ~2000 chars)
        raw_json = state.get('raw_node_json', '{}')
        if len(raw_json) > 2000:
            raw_json = raw_json[:2000] + "\n... [truncated for token limit]"
        
        content = [
            {"type": "text", "text": prompt},
            {"type": "text", "text": f"\n\nComponent Metadata:\n- Name: {state.get('component_name', 'Unknown')}\n- Description: {state.get('component_description', 'N/A')}\n- Dimensions: {state.get('width', 0)}x{state.get('height', 0)}"},
            {"type": "text", "text": f"\n\nFigma JSON Data (truncated if needed):\n{raw_json}"}
        ]
        
        # Add screenshot if available
        screenshot_path = state.get('figma_screenshot')
        if screenshot_path:
            base64_image = self._encode_image_to_base64(screenshot_path)
            if base64_image:
                content.insert(1, {
                    "type": "image_url",
                    "image_url": {
                        "url": base64_image
                    }
                })
            else:
                print(f"⚠️  Skipping screenshot for {state.get('component_name')}: could not encode image")
        
        messages = [{"role": "user", "content": content}]
        return self._make_request(messages, response_format={"type": "json_object"})
    
    def design_query_model(self, prompt, system_prompt=None):
        """Process design query"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self._make_request(messages)
    
    def design_typescript_type(self, prompt, context=None):
        """Generate TypeScript type definitions"""
        if context:
            prompt = f"{context}\n\n{prompt}"
        messages = [{"role": "user", "content": prompt}]
        return self._make_request(messages)
    
    def design_component_model(self, prompt, system_prompt=None, temperature=0.7):
        """Generate component code"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self._make_request(messages, temperature=temperature)