package dev.cookingplanner.plans.entities;

import dev.cookingplanner.plans.dtos.MealType;
import java.time.LocalDate;

public record MealPlan(long id, LocalDate date, MealType mealType, long recipeId, String recipeTitle) {}
