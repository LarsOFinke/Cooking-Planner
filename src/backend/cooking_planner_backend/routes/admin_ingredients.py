"""Ingredient administration routes."""

from fastapi import APIRouter, Response


def router(ingredients):
    api = APIRouter()

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

    return api
