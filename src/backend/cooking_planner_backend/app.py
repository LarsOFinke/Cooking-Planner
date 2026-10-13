"""Create the local FastAPI app from feature services and route controllers."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from cooking_planner_backend.ingredients.service import IngredientStore
from cooking_planner_backend.plans.service import PlanStore
from cooking_planner_backend.recipes.service import RecipeStore
from cooking_planner_backend.errors import ConflictError
from cooking_planner_backend.repositories.storage import Storage
from cooking_planner_backend.routes import ingredient_controller, plan_controller, recipe_controller


def create_app(data_dir: Path, catalog_dir: Path, instance_token: str = '') -> FastAPI:
    storage = Storage(data_dir)
    recipes = RecipeStore(storage, catalog_dir)
    ingredients = IngredientStore(storage, recipes)
    plans = PlanStore(storage, recipes)
    app = FastAPI(title='Cooking Planner local API', docs_url=None, redoc_url=None, openapi_url=None)
    app.state.storage = storage

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
        return {'status': 'ok', 'instanceToken': instance_token}

    app.include_router(recipe_controller.router(recipes))
    app.include_router(plan_controller.router(plans))
    app.include_router(ingredient_controller.router(ingredients))
    return app
