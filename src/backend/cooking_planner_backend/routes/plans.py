"""Meal-plan routes."""

from fastapi import APIRouter, Query, Response


def router(plans):
    api = APIRouter()

    @api.get('/api/plans')
    def plan_list(from_: str = Query(alias='from'), to: str = Query(), locale: str = 'en'):
        return plans.list(from_, to, locale)

    @api.put('/api/plans')
    def save_plan(body: dict):
        return plans.save(body.get('date'), body.get('mealType'), body.get('recipeId'), body.get('servings'))

    @api.delete('/api/plans/{plan_id}', status_code=204)
    def delete_plan(plan_id: int):
        plans.delete(plan_id)
        return Response(status_code=204)

    return api
