package dev.cookingplanner.plans.services;

import dev.cookingplanner.plans.dtos.MealPlanInput;
import dev.cookingplanner.plans.entities.MealPlan;
import dev.cookingplanner.plans.repositories.MealPlanRepository;
import dev.cookingplanner.recipes.repositories.RecipeRepository;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

@Service
public class MealPlanService {
    private final MealPlanRepository plans;
    private final RecipeRepository recipes;
    public MealPlanService(MealPlanRepository plans, RecipeRepository recipes) { this.plans = plans; this.recipes = recipes; }
    public List<MealPlan> list(LocalDate from, LocalDate to) {
        if (to.isBefore(from) || ChronoUnit.DAYS.between(from, to) > 62) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Date range must be at most 62 days");
        return plans.findBetween(from, to).stream().map(this::withTitle).toList();
    }
    public MealPlan save(MealPlanInput input) {
        if (recipes.findById(input.recipeId()).isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Recipe not found");
        return withTitle(plans.save(input));
    }
    public void delete(long id) {
        if (plans.delete(id) == 0) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Plan not found");
    }
    private MealPlan withTitle(MealPlan plan) {
        String title = recipes.findById(plan.recipeId()).map(recipe -> recipe.title()).orElse("Missing recipe");
        return new MealPlan(plan.id(), plan.date(), plan.mealType(), plan.recipeId(), title);
    }
}
