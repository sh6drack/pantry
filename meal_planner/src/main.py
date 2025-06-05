import requests
import json
from flask import Flask, render_template_string, request as flask_request

api_key = "5897e80cbbc34d10a19363b0962cafcf"


def get_user_input():
    ingredients = input("Seperated by commas, enter your available ingredients: ")
    ingredient_list = ingredients.split(", ")

    return ingredient_list

def get_user_filters():
    filters = input(
        "gluten-free, ketogenic, vegetarian, lacto-vegetarian, ovo-vegetarian, \
vegan, pescetarian, paleo, lowFODMAP, whole30 ; Seperated by commas, enter your \
desired dietary filters(If none, leave blank): ")
    filter_list = filters.split(", ")

    return filter_list

def make_ingredient_api_call(ingredients, filters = []): 
    #ingredients argument requieed by findbyingredient spoonacular endpoint
    #filters optional & serves as optional additional criteria, []
    url = "https://api.spoonacular.com/recipes/findByIngredients"
    if not isinstance(ingredients, list):
        raise TypeError("ingredients must be in a list")
    
    params = {
        "apiKey": api_key,
        "ingredients": ",".join(ingredients),
        #"number" : 5
        "diet" : ",".join(filters) if filters else None
    }

    response = requests.get(url, params = params)
    return response

def make_recipe_info_api_call(recipe_id):
    url = f"https://api.spoonacular.com/recipes/{recipe_id}/information?includeNutrition=true"
    params = {
        "apiKey": api_key
    }

    response = requests.get(url, params = params)
    return response


def process_response(response):
    if response.status_code == 200:
        data = response.json()

        title = data.get("title", "no title found")
        image_url = data.get("image", "")
        summary = data.get("summary", "")
        ingredients = data.get("extendedIngredients", [])
        nutrition = data.get("nutrition", {}).get("nutrients", []) 
        #nutrition is a dictionary

        print(f"\nTitle: {title}")
        # print(f"Image: {image_url}")
        print(f"\nSummary: {summary}")
        print("Ingredients:")
        for ingredient in ingredients:
            name = ingredient.get("name", "unkown")
            amount = ingredient.get("amount", "n/a")
            unit = ingredient.get("unit", "")
            print(f"- {name}: {amount} {unit}")

        nutrition = data.get("nutrition", {})  
        # nutrition holds nested structure
        nutrients = nutrition.get("nutrients", []) 
        # nutrition has key "nutrients" --
        # nutrients is a list of small dictionaries with keys name amount unit
        # so, "for each _ in nutrients" -
        if nutrients:
            print("\nNutritional Information:")
            for nutrient in nutrients:
                name = nutrient.get("name", "")
                amount = nutrient.get("amount", "NA")
                unit = nutrient.get("unit", "")
                if amount != 0:
                    print(f"- {name}: {amount} {unit}")
        else:
            print("\nNo nutritional information available")
    else:
        print(f"Error: {response.status_code}")
        return None 

def run_cli():
    ingredients = get_user_input()
    filters = get_user_filters() 
    recipe_data_response = make_ingredient_api_call(ingredients, filters)

    if recipe_data_response.status_code == 200:
        recipe_data = recipe_data_response.json()

        if recipe_data:
            for recipe in recipe_data:
                recipe_id = recipe["id"]
                recipe_info_response = make_recipe_info_api_call(recipe_id)
                process_response(recipe_info_response)
                print("\n\n---\n\n")
        else: 
            print("No recipes found.")
    else:
        print(f"Error: {recipe_data_response.status_code}")

# Minimal Flask app
app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Meal Planner</title>
    <style>
        body {
            background: #f5f5dc;
            min-height: 100vh;
            margin: 0;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .center-box {
            background: white;
            padding: 2rem 2.5rem;
            border-radius: 12px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.07);
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        input[type="text"] {
            width: 300px;
            padding: 0.5rem;
            font-size: 1rem;
            border-radius: 6px;
            border: 1px solid #ccc;
            margin-bottom: 1rem;
        }
        button {
            background: #f5f5dc;
            border: none;
            padding: 0.5rem 1.5rem;
            border-radius: 6px;
            font-size: 1rem;
            cursor: pointer;
        }
        .results {
            margin-top: 2rem;
            text-align: left;
        }
    </style>
</head>
<body>
    <form method="POST">
        <div class="center-box">
            <h2>Enter your ingredients</h2>
            <input type="text" name="ingredients" placeholder="e.g. tomato, cheese, bread" required>
            <button type="submit">Find Recipes</button>
            {% if results %}
            <div class="results">
                {{ results|safe }}
            </div>
            {% endif %}
        </div>
    </form>
</body>
</html>
'''

def get_recipes_html(ingredients):
    # No filters for now, just ingredients
    response = make_ingredient_api_call(ingredients)
    if response.status_code == 200:
        recipe_data = response.json()
        if recipe_data:
            html = ""
            for recipe in recipe_data:
                recipe_id = recipe["id"]
                recipe_info_response = make_recipe_info_api_call(recipe_id)
                if recipe_info_response.status_code == 200:
                    data = recipe_info_response.json()
                    title = data.get("title", "no title found")
                    image_url = data.get("image", "")
                    summary = data.get("summary", "")
                    html += f'<h3>{title}</h3>'
                    if image_url:
                        html += f'<img src="{image_url}" alt="{title}" style="max-width:200px;"><br>'
                    html += f'<div>{summary}</div><hr>'
            return html
        else:
            return "No recipes found."
    else:
        return f"Error: {response.status_code}"

@app.route('/', methods=['GET', 'POST'])
def index():
    results = None
    if flask_request.method == 'POST':
        ingredients = flask_request.form['ingredients']
        ingredient_list = [i.strip() for i in ingredients.split(',') if i.strip()]
        results = get_recipes_html(ingredient_list)
    return render_template_string(HTML_TEMPLATE, results=results)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'web':
        app.run(debug=True, host='0.0.0.0', port=8080)
    else:
        run_cli()