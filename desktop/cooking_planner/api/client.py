import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.parse import quote
from urllib.request import Request, urlopen


class ApiClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8765") -> None:
        self.base_url = base_url.rstrip("/")

    def request(self, method: str, path: str, payload: object | None = None) -> object:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(self.base_url + path, data=body, method=method,
                          headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=10) as response:
                data = response.read()
                return json.loads(data) if data else None
        except HTTPError as error:
            if path.startswith("/api/admin/"):
                try:
                    message = json.loads(error.read()).get('message')
                except (ValueError, AttributeError):
                    message = None
                raise RuntimeError(message or f"Recipe change failed ({error.code}).") from error
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
