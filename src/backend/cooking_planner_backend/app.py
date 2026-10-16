"""Create the local FastAPI app from feature services and route controllers."""

from pathlib import Path
from secrets import compare_digest

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from cooking_planner_backend.ingredients.IngredientStore import IngredientStore
from cooking_planner_backend.plans.PlanStore import PlanStore
from cooking_planner_backend.recipes.RecipeStore import RecipeStore
from cooking_planner_backend.ConflictError import ConflictError
from cooking_planner_backend.repositories.Storage import Storage
from cooking_planner_backend.routes import (admin_ingredients, admin_recipes, ingredients as ingredient_routes,
                                            plans as plan_routes, prices, recipes as recipe_routes, shopping)


def create_app(data_dir: Path, catalog_dir: Path, instance_token: str) -> FastAPI:
    if not instance_token:
        raise ValueError('A local API token is required')
    storage = Storage(data_dir)
    recipes = RecipeStore(storage, catalog_dir)
    ingredients = IngredientStore(storage, recipes)
    plans = PlanStore(storage, recipes)
    app = FastAPI(title='Cooking Planner local API', docs_url=None, redoc_url=None, openapi_url=None,
                  telemetry={'tracing': False, 'metrics': False, 'logs': False,
                             'operation_spans': False, 'auto_configure': False})
    app.state.storage = storage

    @app.middleware('http')
    async def require_local_token(request: Request, call_next):
        supplied = request.headers.get('X-Cooking-Planner-Token', '')
        if not compare_digest(supplied, instance_token):
            return JSONResponse(status_code=403, content={'message': 'Local API access denied'})
        return await call_next(request)

    @app.exception_handler(ValueError)
    async def bad_input(_: Request, error: ValueError):
        return JSONResponse(status_code=400, content={'message': str(error)})

    @app.exception_handler(ConflictError)
    async def conflict(_: Request, error: ConflictError):
        return JSONResponse(status_code=409, content={'message': str(error)})

    @app.exception_handler(LookupError)
    async def missing(_: Request, error: LookupError):
        return JSONResponse(status_code=404, content={'message': str(error)})

    @app.get('/api/health')
    def health():
        return {'status': 'ok'}

    app.include_router(recipe_routes.router(recipes))
    app.include_router(admin_recipes.router(recipes))
    app.include_router(shopping.router(plans))
    app.include_router(plan_routes.router(plans))
    app.include_router(ingredient_routes.router(ingredients))
    app.include_router(prices.router(ingredients))
    app.include_router(admin_ingredients.router(ingredients))
    return app
