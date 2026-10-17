"""Recipe administration routes."""

from fastapi import APIRouter, Response


def router(recipes):
    api = APIRouter()

    @api.get('/api/admin/recipes')
    def admin_recipes():
        return recipes.admin_list()

    @api.get('/api/admin/recipes/options')
    def admin_options():
        return recipes.options()

    @api.get('/api/admin/recipes/{recipe_id}')
    def admin_recipe(recipe_id: str):
        return recipes.admin_get(recipe_id)

    @api.post('/api/admin/recipes/{recipe_id}', status_code=201)
    def create_recipe(recipe_id: str, body: dict):
        return recipes.save(recipe_id, body.get('sourceLocale'), body.get('translations'), True,
                            body.get('imageUploads'))

    @api.put('/api/admin/recipes/{recipe_id}')
    def update_recipe(recipe_id: str, body: dict):
        return recipes.save(recipe_id, body.get('sourceLocale'), body.get('translations'), False,
                            body.get('imageUploads'))

    @api.delete('/api/admin/recipes/{recipe_id}', status_code=204)
    def delete_recipe(recipe_id: str):
        recipes.delete(recipe_id)
        return Response(status_code=204)

    return api
