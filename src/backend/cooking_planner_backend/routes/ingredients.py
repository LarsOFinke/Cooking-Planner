"""Public ingredient search and creation routes."""

from fastapi import APIRouter


def router(ingredients):
    api = APIRouter()

    @api.get('/api/ingredients')
    def search_ingredients(locale: str = 'en', q: str = ''):
        return ingredients.search(locale, q)

    @api.post('/api/ingredients', status_code=201)
    def create_ingredient(body: dict):
        return ingredients.create(body.get('id'), body.get('locale'), body.get('name'))

    return api
