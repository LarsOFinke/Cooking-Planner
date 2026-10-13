"""Public recipe catalog routes."""

from fastapi import APIRouter


def router(recipes):
    api = APIRouter()

    @api.get('/api/recipes/locales')
    def locales():
        return recipes.locales()

    @api.get('/api/recipes/info')
    def catalog_info(locale: str = 'en'):
        return recipes.info(locale)

    @api.get('/api/recipes')
    def recipe_list(locale: str = 'en'):
        return recipes.list(locale)

    @api.get('/api/recipes/{recipe_id}')
    def recipe_get(recipe_id: str, locale: str = 'en'):
        return recipes.get(locale, recipe_id)

    return api
