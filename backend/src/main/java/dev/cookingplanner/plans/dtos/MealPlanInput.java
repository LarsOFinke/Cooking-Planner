package dev.cookingplanner.plans.dtos;

import jakarta.validation.constraints.NotNull;
import java.time.LocalDate;

public record MealPlanInput(@NotNull LocalDate date, @NotNull MealType mealType, @NotNull Long recipeId) {}
