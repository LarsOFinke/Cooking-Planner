import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ApiClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8765") -> None:
        self.base_url = base_url.rstrip("/")

    def request(self, method: str, path: str, payload: object | None = None) -> object:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            self.base_url + path,
            data=body,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=8) as response:
                data = response.read()
                return json.loads(data) if data else None
        except HTTPError as error:
            raise RuntimeError(f"API returned {error.code}. Check the entered data.") from error
        except URLError as error:
            raise RuntimeError("Cannot reach the local backend. Start it and retry.") from error

    def locales(self) -> list[str]:
        return self.request("GET", "/api/recipes/locales")

    def recipes(self, locale: str) -> list[dict]:
        return self.request("GET", "/api/recipes?" + urlencode({"locale": locale}))

    def save_recipe(self, payload: dict, locale: str, recipe_id: int | None = None) -> dict:
        return self.request("PUT" if recipe_id else "POST", f"/api/recipes/{recipe_id}" if recipe_id else "/api/recipes?" + urlencode({"locale": locale}), payload)

    def import_recipes(self, recipes: list[dict], locale: str) -> list[dict]:
        return self.request("POST", "/api/recipes/import?" + urlencode({"locale": locale}), recipes)

    def plans(self, start: str, end: str) -> list[dict]:
        return self.request("GET", "/api/plans?" + urlencode({"from": start, "to": end}))

    def save_plan(self, date: str, meal_type: str, recipe_id: int) -> dict:
        return self.request("PUT", "/api/plans", {"date": date, "mealType": meal_type, "recipeId": recipe_id})
