from flask import render_template, request
import re
from main import app, quota_manager, search_recipes_efficiently, MAX_DAILY_REQUESTS

def format_recipes_for_web(recipes):
    """Format recipes for web display"""
    if not recipes:
        return '<div class="error">No recipes found with those ingredients.</div>'
    
    html = f'<h2>Found {len(recipes)} recipes:</h2>'
    
    for recipe in recipes:
        title = recipe.get("title", "No title")
        image_url = recipe.get("image", "")
        summary = recipe.get("summary", "No description available")
        
        # Clean up HTML tags from summary
        summary = re.sub('<.*?>', '', summary)[:200] + "..."
        
        html += f'''
        <div class="recipe">
            <h3>{title}</h3>
            {f'<img src="{image_url}" alt="{title}">' if image_url else ''}
            <p>{summary}</p>
        </div>
        '''
    
    return html

@app.route('/', methods=['GET', 'POST'])
def web_app():
    """Efficient web app route"""
    results = None
    
    if request.method == 'POST':
        if not quota_manager.can_make_request():
            results = '<div class="error">❌ Daily API quota exceeded! Try again tomorrow.</div>'
        else:
            ingredients_input = request.form.get('ingredients', '').strip()
            if ingredients_input:
                ingredients = [i.strip() for i in ingredients_input.split(',') if i.strip()]
                recipes = search_recipes_efficiently(ingredients, max_recipes=3)
                results = format_recipes_for_web(recipes)
            else:
                results = '<div class="error">Please enter some ingredients!</div>'
    
    return render_template(
        'index.html',
        results=results,
        remaining_requests=quota_manager.get_remaining_requests(),
        max_requests=MAX_DAILY_REQUESTS
    ) 