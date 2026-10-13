"""Ingredient and price HTTP controllers."""

from fastapi import APIRouter, Response


def router(ingredients):
    api = APIRouter()

    @api.get('/api/ingredients')
    def search_ingredients(locale: str = 'en', q: str = ''):
        return ingredients.search(locale, q)

    @api.post('/api/ingredients', status_code=201)
    def create_ingredient(body: dict):
        return ingredients.create(body.get('id'), body.get('locale'), body.get('name'))

    @api.get('/api/admin/ingredients')
    def admin_ingredients(q: str = ''):
        return ingredients.catalog(q)

    @api.get('/api/admin/ingredients/{ingredient_id}')
    def admin_ingredient(ingredient_id: str):
        return ingredients.catalog_entry(ingredient_id)

    @api.put('/api/admin/ingredients/{ingredient_id}')
    def save_admin_ingredient(ingredient_id: str, body: dict):
        return ingredients.save_catalog_entry(ingredient_id, body.get('translations'))

    @api.delete('/api/admin/ingredients/{ingredient_id}', status_code=204)
    def delete_admin_ingredient(ingredient_id: str):
        ingredients.delete_catalog_entry(ingredient_id)
        return Response(status_code=204)

    @api.get('/api/ingredients/prices')
    def prices(week: str):
        return ingredients.prices(week)

    @api.get('/api/ingredients/reference-prices')
    def reference_prices():
        return ingredients.reference_prices()

    @api.put('/api/ingredients/{ingredient_id}/reference-prices')
    def save_reference_price(ingredient_id: str, unit: str, body: dict):
        ingredients.save_price(ingredient_id, '*', unit, body.get('price'), body.get('basisQuantity'))

    @api.put('/api/ingredients/{ingredient_id}/prices')
    def save_price(ingredient_id: str, week: str, unit: str, body: dict):
        ingredients.save_price(ingredient_id, week, unit, body.get('price'))

    @api.delete('/api/ingredients/prices', status_code=204)
    def clear_prices(week: str):
        ingredients.clear_prices(week)
        return Response(status_code=204)

    return api
