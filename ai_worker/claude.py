import anthropic
from ai_worker.factory import Factory
import base64
import os
from pathlib import Path


class Claude(Factory):
    """Claude provider implementation"""
    
    def __init__(self, model, api_key):
        super().__init__("claude", model, api_key)
        self.client = anthropic.Anthropic(api_key=api_key)
    
    def _make_request(self, messages, system_prompt=None, temperature=0.7, max_tokens=4096):
        """Make API request to Claude"""
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if system_prompt:
            params["system"] = system_prompt
        
        response = self.client.messages.create(**params)
        return response.content[0].text
    
    def _encode_image_to_base64(self, image_path):
        """Convert image file path to base64 for Claude"""
        try:
            # Handle file paths
            if os.path.isfile(image_path):
                with open(image_path, 'rb') as image_file:
                    image_data = image_file.read()
                    base64_image = base64.b64encode(image_data).decode('utf-8')
                    
                    # Detect media type from extension
                    ext = Path(image_path).suffix.lower()
                    media_types = {
                        '.png': 'image/png',
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.gif': 'image/gif',
                        '.webp': 'image/webp'
                    }
                    media_type = media_types.get(ext, 'image/png')
                    
                    return base64_image, media_type
            
            return None, None
        except Exception as e:
            print(f"Warning: Could not encode image {image_path}: {e}")
            return None, None
    
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
            base64_image, media_type = self._encode_image_to_base64(screenshot_path)
            if base64_image and media_type:
                content.insert(1, {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": base64_image
                    }
                })
            else:
                print(f"⚠️  Skipping screenshot for {state.get('component_name')}: could not encode image")
        
        messages = [{"role": "user", "content": content}]
        system_prompt = "You must respond with valid JSON in the exact format specified."
        return self._make_request(messages, system_prompt=system_prompt)
    
    def design_query_model(self, prompt, system_prompt=None):
        """Process design query"""
        messages = [{"role": "user", "content": prompt}]
        return self._make_request(messages, system_prompt=system_prompt)
    
    def design_typescript_type(self, prompt, context=None):
        """Generate TypeScript type definitions"""
        if context:
            prompt = f"{context}\n\n{prompt}"
        messages = [{"role": "user", "content": prompt}]
        return self._make_request(messages)
    
    def design_component_model(self, prompt, system_prompt=None, temperature=0.7):
        """Generate component code"""
        messages = [{"role": "user", "content": prompt}]
        return self._make_request(messages, system_prompt=system_prompt, temperature=temperature)