"""Mock weather tool for demonstration of dynamic tool loading."""

from typing import Any
import random
from tools.base import Tool


class WeatherTool(Tool):
    """A mock weather tool that returns simulated weather data."""
    
    def __init__(self):
        super().__init__(
            name="weather",
            description="Get current weather information for a location (mock data for demo)",
            input_schema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name or location to get weather for"
                    }
                },
                "required": ["location"]
            }
        )
        
        # Mock weather conditions
        self.conditions = ["Sunny", "Partly Cloudy", "Cloudy", "Rainy", "Stormy", "Snowy", "Foggy"]
        
    async def execute(self, location: str) -> str:
        """Return mock weather data."""
        # Generate mock data
        temp_f = random.randint(20, 95)
        temp_c = round((temp_f - 32) * 5/9)
        condition = random.choice(self.conditions)
        humidity = random.randint(30, 90)
        wind_speed = random.randint(0, 25)
        
        return f"""Weather for {location}:
🌡️  Temperature: {temp_f}°F ({temp_c}°C)
☁️  Condition: {condition}
💧 Humidity: {humidity}%
💨 Wind: {wind_speed} mph

Note: This is mock data for demonstration purposes."""