"""Ingredient price routes."""

from fastapi import APIRouter, Response


def router(ingredients):
    api = APIRouter()

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
