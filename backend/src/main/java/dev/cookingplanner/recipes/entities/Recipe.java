package dev.cookingplanner.recipes.entities;

import java.util.List;

public record Recipe(long id, String title, String category, List<String> ingredients, String instructions, int prepMinutes, String locale) {}
