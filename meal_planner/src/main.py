import requests
import json
import time
import os
from functools import lru_cache
from flask import Flask

# Configuration
API_KEY = "5897e80cbbc34d10a19363b0962cafcf"
MAX_DAILY_REQUESTS = 140  # Leave buffer of 10 from 150 limit
REQUEST_COUNT_FILE = "api_usage.txt"

class QuotaManager:
    def __init__(self):
        self.request_count = self.load_today_count()
    
    def load_today_count(self):
        """Load today's request count from file"""
        today = time.strftime('%Y-%m-%d')
        try:
            with open(REQUEST_COUNT_FILE, 'r') as f:
                lines = f.readlines()
                # Count requests from today
                return sum(1 for line in lines if line.startswith(today))
        except FileNotFoundError:
            return 0
    
    def log_request(self):
        """Log a new API request"""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        with open(REQUEST_COUNT_FILE, 'a') as f:
            f.write(f"{timestamp}\n")
        self.request_count += 1
    
    def can_make_request(self):
        """Check if we can make another request"""
        return self.request_count < MAX_DAILY_REQUESTS
    
    def get_remaining_requests(self):
        """Get remaining requests for today"""
        return max(0, MAX_DAILY_REQUESTS - self.request_count)

quota_manager = QuotaManager()

@lru_cache(maxsize=50)
def cached_ingredient_search(ingredients_str, max_recipes=3):
    """Cache ingredient searches to avoid duplicate API calls"""
    if not quota_manager.can_make_request():
        return None
    
    url = "https://api.spoonacular.com/recipes/findByIngredients"
    params = {
        "apiKey": API_KEY,
        "ingredients": ingredients_str,
        "number": max_recipes,
        "ranking": 2,  # Maximize used ingredients
        "ignorePantry": True
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        quota_manager.log_request()
        return response
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return None

def get_bulk_recipe_details(recipe_ids):
    """Get multiple recipe details in one API call instead of individual calls"""
    if not quota_manager.can_make_request():
        return None
    
    if not recipe_ids:
        return None
    
    # Use bulk endpoint - much more efficient
    ids_str = ",".join(map(str, recipe_ids))
    url = "https://api.spoonacular.com/recipes/informationBulk"
    
    params = {
        "apiKey": API_KEY,
        "ids": ids_str,
        "includeNutrition": False  # Skip nutrition to save on response size
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        quota_manager.log_request()
        return response
    except requests.exceptions.RequestException as e:
        print(f"Bulk API request failed: {e}")
        return None

def get_user_input():
    """CLI input for ingredients"""
    ingredients = input("Enter your available ingredients (comma-separated): ")
    return [i.strip() for i in ingredients.split(",") if i.strip()]

def get_user_filters():
    """CLI input for dietary filters"""
    print("Available filters: gluten-free, ketogenic, vegetarian, vegan, pescetarian, paleo")
    filters = input("Enter dietary filters (comma-separated, or leave blank): ")
    return [f.strip() for f in filters.split(",") if f.strip()]

def search_recipes_efficiently(ingredients, max_recipes=3):
    """Efficient recipe search using only 2 API calls maximum"""
    if not ingredients:
        return []
    
    # Check quota first
    if not quota_manager.can_make_request():
        print(f"⚠️ Daily quota exceeded ({quota_manager.request_count}/{MAX_DAILY_REQUESTS})")
        return []
    
    print(f"API requests remaining: {quota_manager.get_remaining_requests()}")
    
    # Step 1: Find recipes by ingredients (1 API call)
    ingredients_str = ",".join(ingredients)
    response = cached_ingredient_search(ingredients_str, max_recipes)
    
    if not response or response.status_code != 200:
        print(f"Failed to find recipes. Status: {response.status_code if response else 'No response'}")
        return []
    
    basic_recipes = response.json()
    if not basic_recipes:
        print("No recipes found with those ingredients.")
        return []
    
    # Step 2: Get detailed info for all recipes (1 more API call)
    recipe_ids = [recipe["id"] for recipe in basic_recipes]
    details_response = get_bulk_recipe_details(recipe_ids)
    
    if details_response and details_response.status_code == 200:
        detailed_recipes = details_response.json()
        print(f"Found {len(detailed_recipes)} recipes using {quota_manager.request_count} API calls")
        return detailed_recipes
    else:
        # Fallback to basic info if bulk fails
        print("Using basic recipe info (bulk details failed)")
        return basic_recipes

def display_recipe(recipe):
    """Display a single recipe in CLI"""
    title = recipe.get("title", "No title")
    summary = recipe.get("summary", "No description available")
    
    # Handle both detailed and basic recipe formats
    if "extendedIngredients" in recipe:
        # Detailed format
        ingredients = recipe.get("extendedIngredients", [])
        ingredient_list = [
            f"- {ing.get('name', 'unknown')}: {ing.get('amount', '')} {ing.get('unit', '')}"
            for ing in ingredients[:8]  # Limit to first 8 ingredients
        ]
    else:
        # Basic format from findByIngredients
        ingredient_list = ["- Check recipe for full ingredient list"]
    
    print(f"\n{'='*50}")
    print(f"🍽️  {title}")
    print(f"{'='*50}")
    print(f"Summary: {summary[:200]}...")
    print("\nIngredients:")
    for ingredient in ingredient_list:
        print(ingredient)

def run_cli():
    """Efficient CLI version"""
    print("🍽️  Efficient Meal Planner")
    print(f"API requests remaining today: {quota_manager.get_remaining_requests()}")
    
    if not quota_manager.can_make_request():
        print("❌ Daily API quota exceeded. Try again tomorrow!")
        return
    
    ingredients = get_user_input()
    if not ingredients:
        print("No ingredients provided!")
        return
    
    # Get recipes efficiently
    recipes = search_recipes_efficiently(ingredients, max_recipes=3)
    
    if recipes:
        print(f"\n✅ Found {len(recipes)} recipes!")
        for recipe in recipes:
            display_recipe(recipe)
    else:
        print("❌ No recipes found.")
    
    print(f"\n📊 API calls used: {quota_manager.request_count}/{MAX_DAILY_REQUESTS}")

# Flask Web App
app = Flask(__name__)

# Import routes after app is created
from routes import *

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'web':
        print(f"🚀 Starting web app with {quota_manager.get_remaining_requests()} API calls remaining")
        app.run(debug=True, host='0.0.0.0', port=8080)
    else:
        run_cli()