package dev.cookingplanner.plans.entities;

import java.math.BigDecimal;

public record ShoppingItem(String ingredientId, String name, BigDecimal amount, String unit, int recipeCount) {}
