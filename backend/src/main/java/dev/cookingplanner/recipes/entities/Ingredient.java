package dev.cookingplanner.recipes.entities;

import java.math.BigDecimal;

public record Ingredient(String name, String ingredientId, BigDecimal amount, String unit) {}
