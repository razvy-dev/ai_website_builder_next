from google import genai
from google.genai import types
from ai_worker.factory import Factory
import os
from pathlib import Path


class Gemini(Factory):
    """Gemini provider implementation"""
    
    def __init__(self, model, api_key):
        super().__init__("gemini", model, api_key)
        self.client = genai.Client(api_key=api_key)
        self.model = model
    
    def _make_request(self, prompt, temperature=0.7):
        """Make API request to Gemini"""
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature
            )
        )
        return response.text
    
    def _read_image_file(self, image_path):
        """Read image file and return inline data part for Gemini"""
        try:
            if os.path.isfile(image_path):
                with open(image_path, 'rb') as image_file:
                    image_data = image_file.read()
                    
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
                    
                    return types.Part.from_bytes(data=image_data, mime_type=mime_type)
            return None
        except Exception as e:
            print(f"Warning: Could not read image {image_path}: {e}")
            return None
    
    def design_sanity_schema_model(self, prompt, state):
        """Design sanity schema validation"""
        # Truncate raw_node_json to prevent token overflow (max ~2000 chars)
        raw_json = state.get('raw_node_json', '{}')
        if len(raw_json) > 2000:
            raw_json = raw_json[:2000] + "\n... [truncated for token limit]"
        
        parts = [prompt]
        parts.append(f"\n\nComponent Metadata:\n- Name: {state.get('component_name', 'Unknown')}\n- Description: {state.get('component_description', 'N/A')}\n- Dimensions: {state.get('width', 0)}x{state.get('height', 0)}")
        parts.append(f"\n\nFigma JSON Data (truncated if needed):\n{raw_json}")
        
        # Add screenshot if available
        screenshot_path = state.get('figma_screenshot')
        if screenshot_path:
            image_part = self._read_image_file(screenshot_path)
            if image_part:
                parts.insert(1, image_part)
            else:
                print(f"⚠️  Skipping screenshot for {state.get('component_name')}: could not read image")
        
        combined_prompt = parts if any(isinstance(p, types.Part) for p in parts) else "\n".join(parts)
        return self._make_request(combined_prompt)
    
    def design_query_model(self, prompt, system_prompt=None):
        """Process design query"""
        if system_prompt:
            prompt = f"{system_prompt}\n\n{prompt}"
        return self._make_request(prompt)
    
    def design_typescript_type(self, prompt, context=None):
        """Generate TypeScript type definitions"""
        if context:
            prompt = f"{context}\n\n{prompt}"
        return self._make_request(prompt)
    
    def design_component_model(self, prompt, system_prompt=None, temperature=0.7):
        """Generate component code"""
        if system_prompt:
            prompt = f"{system_prompt}\n\n{prompt}"
        return self._make_request(prompt, temperature=temperature)