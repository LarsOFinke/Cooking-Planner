package dev.cookingplanner.plans.services;

import dev.cookingplanner.plans.entities.ShoppingItem;
import dev.cookingplanner.recipes.repositories.RecipeRepository;
import dev.cookingplanner.recipes.services.IngredientService;
import java.time.LocalDate;
import java.util.Comparator;
import java.util.HashMap;
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
        Map<String, ShoppingItem> items = new HashMap<>();
        for (var plan : plans.list(from, to, locale)) {
            var recipe = recipes.findById(locale, plan.recipeId());
            if (recipe.isEmpty()) continue;
            var localized = ingredients == null ? recipe.get() : ingredients.localize(recipe.get());
            for (var ingredient : localized.ingredients()) {
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
