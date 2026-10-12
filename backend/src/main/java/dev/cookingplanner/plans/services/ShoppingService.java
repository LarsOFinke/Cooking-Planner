package dev.cookingplanner.plans.services;

import dev.cookingplanner.plans.entities.ShoppingItem;
import dev.cookingplanner.recipes.entities.Recipe;
import dev.cookingplanner.recipes.repositories.RecipeRepository;
import dev.cookingplanner.recipes.services.IngredientService;
import java.time.LocalDate;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

@Service
public class ShoppingService {
    private final MealPlanService plans;
    private final RecipeRepository recipes;
    private final IngredientService ingredients;
    @Autowired
    public ShoppingService(MealPlanService plans, RecipeRepository recipes, IngredientService ingredients) {
        this.plans = plans; this.recipes = recipes; this.ingredients = ingredients;
    }
    public ShoppingService(MealPlanService plans, RecipeRepository recipes) {
        this(plans, recipes, null);
    }
    public List<ShoppingItem> list(LocalDate from, LocalDate to, String locale) {
        var week = plans.list(from, to, locale);
        Map<String, Recipe> plannedRecipes = new LinkedHashMap<>();
        for (var plan : week)
            if (!plannedRecipes.containsKey(plan.recipeId()))
                recipes.findById(locale, plan.recipeId()).ifPresent(recipe ->
                    plannedRecipes.put(plan.recipeId(), recipe));
        if (ingredients != null) {
            List<Recipe> localized = ingredients.localizeAll(List.copyOf(plannedRecipes.values()));
            localized.forEach(recipe -> plannedRecipes.put(recipe.id(), recipe));
        }
        Map<String, ShoppingItem> items = new HashMap<>();
        for (var plan : week) {
            Recipe recipe = plannedRecipes.get(plan.recipeId());
            if (recipe == null) continue;
            for (var ingredient : recipe.ingredients()) {
                String key = ingredient.ingredientId() + ":" + ingredient.unit();
                var previous = items.get(key);
                var amount = ingredient.amount().multiply(java.math.BigDecimal.valueOf(plan.servings()));
                items.put(key, previous == null
                    ? new ShoppingItem(ingredient.ingredientId(), ingredient.name(), amount, ingredient.unit(), 1)
                    : new ShoppingItem(previous.ingredientId(), previous.name(), previous.amount().add(amount), previous.unit(), previous.recipeCount() + 1));
            }
        }
        return items.values().stream().sorted(Comparator.comparing(ShoppingItem::name, String.CASE_INSENSITIVE_ORDER)).toList();
    }
}
