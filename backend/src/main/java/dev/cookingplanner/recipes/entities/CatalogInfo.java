package dev.cookingplanner.recipes.entities;

public record CatalogInfo(
    String locale, String dataset, int recipeCount, int countryCount, int regionCount,
    String quantityNote, String dietNote, String originNote, String quality
) {}
