import random
from datetime import datetime

def get_weather_forecast(city: str, date_str: str) -> dict:
    """
    Returns a mock weather forecast for a given city and date.
    Args:
        city: The name of the city.
        date_str: Date in YYYY-MM-DD format.
    """
    # Parse date to get month for seasonal simulation
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        month = dt.month
    except ValueError:
        month = 6 # Default to summer

    city_lower = city.lower()
    
    # Simple seasonal simulation by city type
    if "seattle" in city_lower or "london" in city_lower:
        if month in [11, 12, 1, 2]:
            condition = "Rainy"
            temp = random.randint(38, 48)
            precip = random.randint(70, 95)
        elif month in [6, 7, 8, 9]:
            condition = "Sunny"
            temp = random.randint(70, 85)
            precip = random.randint(5, 20)
        else:
            condition = "Cloudy"
            temp = random.randint(50, 65)
            precip = random.randint(40, 60)
    elif "miami" in city_lower or "hawaii" in city_lower or "honolulu" in city_lower:
        if month in [6, 7, 8, 9]:
            condition = "Humid/Thunderstorms"
            temp = random.randint(85, 92)
            precip = random.randint(60, 80)
        else:
            condition = "Sunny"
            temp = random.randint(75, 84)
            precip = random.randint(10, 30)
    else:
        # Default generic simulation based on hemisphere (assuming northern hemisphere for simplicity)
        if month in [12, 1, 2]:
            condition = "Cold/Overcast"
            temp = random.randint(30, 45)
            precip = random.randint(30, 50)
        elif month in [6, 7, 8]:
            condition = "Sunny"
            temp = random.randint(75, 90)
            precip = random.randint(10, 30)
        else:
            condition = "Partly Cloudy"
            temp = random.randint(55, 72)
            precip = random.randint(20, 40)

    return {
        "city": city,
        "date": date_str,
        "temperature_f": temp,
        "temperature_c": round((temp - 32) * 5 / 9, 1),
        "condition": condition,
        "precipitation_probability": f"{precip}%",
        "description": f"Expected to be {condition.lower()} with a temperature around {temp}°F ({round((temp-32)*5/9)}°C)."
    }
