import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.parse import quote
from urllib.request import Request

from cooking_planner.api.local_http import open_local


class ApiClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8765", token: str = '') -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    def request(self, method: str, path: str, payload: object | None = None) -> object:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(self.base_url + path, data=body, method=method,
                          headers={"Content-Type": "application/json",
                                   "X-Cooking-Planner-Token": self.token})
        try:
            with open_local(request, timeout=10) as response:
                data = response.read()
                return json.loads(data) if data else None
        except HTTPError as error:
            if path.startswith("/api/admin/"):
                try:
                    message = json.loads(error.read()).get('message')
                except (ValueError, AttributeError):
                    message = None
                raise RuntimeError(message or f"Admin change failed ({error.code}).") from error
            raise RuntimeError(f"Request failed ({error.code}). Check the selected recipe and date.") from error
        except URLError as error:
            raise RuntimeError("Cannot reach the local backend. Restart the app and try again.") from error

    def locales(self) -> list[str]:
        return self.request("GET", "/api/recipes/locales")

    def recipes(self, locale: str) -> list[dict]:
        return self.request("GET", "/api/recipes?" + urlencode({"locale": locale}))

    def catalog_info(self, locale: str) -> dict:
        return self.request("GET", "/api/recipes/info?" + urlencode({"locale": locale}))

    def plans(self, start: str, end: str, locale: str) -> list[dict]:
        return self.request("GET", "/api/plans?" + urlencode({"from": start, "to": end, "locale": locale}))

    def shopping(self, start: str, end: str, locale: str) -> list[dict]:
        return self.request("GET", "/api/plans/shopping?" + urlencode({"from": start, "to": end, "locale": locale}))

    def ingredients(self, locale: str, query: str) -> list[dict]:
        return self.request("GET", "/api/ingredients?" + urlencode({"locale": locale, "q": query}))

    def register_ingredient(self, ingredient_id: str, locale: str, name: str) -> dict:
        return self.request("POST", "/api/ingredients",
                            {"id": ingredient_id, "locale": locale, "name": name})

    def ingredient_prices(self, week: str) -> dict[str, str]:
        return self.request("GET", "/api/ingredients/prices?" + urlencode({"week": week}))

    def reference_prices(self) -> dict[str, dict]:
        return self.request("GET", "/api/ingredients/reference-prices")

    def save_reference_price(self, key: str, price: str, basis_quantity: int) -> None:
        ingredient_id, unit = key.rsplit(':', 1)
        self.request("PUT", "/api/ingredients/" + quote(ingredient_id, safe="") +
                     "/reference-prices?" + urlencode({"unit": unit}),
                     {"price": price, "basisQuantity": basis_quantity})

    def save_ingredient_price(self, week: str, key: str, price: str) -> None:
        ingredient_id, unit = key.rsplit(':', 1)
        self.request("PUT", "/api/ingredients/" + quote(ingredient_id, safe="") + "/prices?" +
                     urlencode({"week": week, "unit": unit}), {"price": price})

    def clear_ingredient_prices(self, week: str) -> None:
        self.request("DELETE", "/api/ingredients/prices?" + urlencode({"week": week}))

    def save_plan(self, date: str, meal_type: str, recipe_id: str, servings: int) -> dict:
        return self.request("PUT", "/api/plans", {"date": date, "mealType": meal_type,
                                                  "recipeId": recipe_id, "servings": servings})

    def delete_plan(self, plan_id: int) -> None:
        self.request("DELETE", f"/api/plans/{plan_id}")

    def admin_recipes(self) -> list[dict]:
        return self.request("GET", "/api/admin/recipes")

    def admin_options(self) -> dict:
        return self.request("GET", "/api/admin/recipes/options")

    def admin_recipe(self, recipe_id: str) -> dict:
        return self.request("GET", "/api/admin/recipes/" + quote(recipe_id, safe=""))

    def save_recipe(self, recipe_id: str, source_locale: str, translations: dict, create: bool) -> dict:
        return self.request("POST" if create else "PUT", "/api/admin/recipes/" + quote(recipe_id, safe=""),
                            {"sourceLocale": source_locale, "translations": translations})

    def delete_recipe(self, recipe_id: str) -> None:
        self.request("DELETE", "/api/admin/recipes/" + quote(recipe_id, safe=""))

    def admin_ingredients(self, query: str = '') -> list[dict]:
        return self.request("GET", "/api/admin/ingredients?" + urlencode({"q": query}))

    def admin_ingredient(self, ingredient_id: str) -> dict:
        return self.request("GET", "/api/admin/ingredients/" + quote(ingredient_id, safe=""))

    def save_admin_ingredient(self, ingredient_id: str, translations: dict[str, str]) -> dict:
        return self.request("PUT", "/api/admin/ingredients/" + quote(ingredient_id, safe=""),
                            {"translations": translations})

    def delete_admin_ingredient(self, ingredient_id: str) -> None:
        self.request("DELETE", "/api/admin/ingredients/" + quote(ingredient_id, safe=""))
