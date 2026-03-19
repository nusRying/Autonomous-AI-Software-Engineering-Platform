import base64
import os
import time
import cv2
import numpy as np
from typing import Optional, Dict, Any, List
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_manager.rotator import call_llm
from app.config import settings
from app.observability.prometheus import MetricsTracker

class VisionEngineer:
    def __init__(self, db: AsyncSession):
        self.db = db
        # Vision usually requires specific models like gpt-4o or claude-3-5-sonnet
        self.model = "gpt-4o" 
        self.provider = "openai"

    def analyze_layout(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Uses OpenCV to extract structural hints from the image.
        """
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # 1. Detect Contours (Boxes/Components)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 50, 150)
        
        contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        boxes = []
        for c in contours:
            (x, y, w, h) = cv2.boundingRect(c)
            if w > 20 and h > 20: # Filter noise
                boxes.append({"x": int(x), "y": int(y), "w": int(w), "h": int(h)})
        
        # 2. Extract Dominant Colors (Simple K-Means simulation or mean)
        # For simplicity, we'll just take the mean color of the center
        height, width, _ = img.shape
        center_color = img[height//2, width//2].tolist() # BGR
        avg_color_hex = '#{:02x}{:02x}{:02x}'.format(center_color[2], center_color[1], center_color[0])
        
        return {
            "component_count": len(boxes),
            "estimated_boxes": boxes[:10], # Send top 10 for context
            "dominant_color": avg_color_hex,
            "resolution": {"width": width, "height": height}
        }

    async def screenshot_to_code(self, image_bytes: bytes, context_description: Optional[str] = None) -> str:
        """
        Takes screenshot bytes and returns a functional React/Tailwind component.
        """
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        # Get structural hints via OpenCV
        hints = self.analyze_layout(image_bytes)
        
        # Load Design System Context (Mocking file reads for speed or actual read)
        # In production, these would be loaded once in __init__
        design_system_context = """
        PLATFORM DESIGN SYSTEM:
        - Theme: Dark Mode (Slate 900)
        - Primary Color: Sky 500 (#0ea5e9)
        - Aesthetic: Glassmorphism / Modern SAAS
        - Borders: Suble Slate 700/800 with slight transparency
        """

        prompt = f"""
        You are a Senior Frontend Engineer and UI/UX Expert. 
        Analyze the attached screenshot and reconstruct it perfectly using React and Tailwind CSS.
        
        {design_system_context}

        Structural hints from computer vision analysis:
        - Detected {hints['component_count']} primary UI regions.
        - Dominant theme color identified: {hints['dominant_color']}
        - Original Resolution: {hints['resolution']['width']}x{hints['resolution']['height']}

        Requirements:
        1. Output ONLY the code for a single file React component.
        2. Use Lucide React for icons.
        3. STRICTLY follow the Platform Design System (Glassmorphism, Dark Mode).
        4. Include state management for simple interactions (e.g., button clicks, form inputs).
        5. Context: {context_description or "General UI reconstruction"}

        Return the code inside markdown backticks.
        """

        # LiteLLM supports image data in messages for vision models
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                    }
                ]
            }
        ]

        try:
            logger.info("Sending vision request to LLM with structural hints...")
            response_text = await call_llm(
                db=self.db,
                messages=messages,
                provider=self.provider,
                model=self.model
            )
            
            # Extract code from markdown
            if "```jsx" in response_text:
                code = response_text.split("```jsx")[1].split("```")[0].strip()
            elif "```javascript" in response_text:
                code = response_text.split("```javascript")[1].split("```")[0].strip()
            elif "```tsx" in response_text:
                code = response_text.split("```tsx")[1].split("```")[0].strip()
            elif "```" in response_text:
                code = response_text.split("```")[1].split("```")[0].strip()
            else:
                code = response_text.strip()
                
            logger.info("Successfully converted screenshot to code.")
            return code
        except Exception as e:
            logger.error(f"Vision processing failed: {e}")
            return f"/* Error generating code: {e} */"
