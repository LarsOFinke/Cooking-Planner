package dev.cookingplanner.plans.dtos;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Max;
import java.time.LocalDate;

public record MealPlanInput(@NotNull LocalDate date, @NotNull MealType mealType,
    @NotBlank String recipeId, @Min(1) @Max(20) int servings) {}
