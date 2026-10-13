"""Shopping projection from planned meals."""

from fastapi import APIRouter, Query


def router(plans):
    api = APIRouter()

    @api.get('/api/plans/shopping')
    def shopping(from_: str = Query(alias='from'), to: str = Query(), locale: str = 'en'):
        return plans.shopping(from_, to, locale)

    return api
