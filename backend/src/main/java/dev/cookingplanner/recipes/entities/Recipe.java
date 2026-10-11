package dev.cookingplanner.recipes.entities;

import java.util.List;

public record Recipe(
    String id, String name, String country, String countryCode, String region, String continent,
    String category, String categoryLabel, String difficulty, String difficultyLabel,
    String effort, String effortLabel, String dietType, String dietTypeLabel,
    List<String> suitableFor, List<String> suitableForLabels, List<Ingredient> ingredients,
    int prepMinutes, int cookMinutes, int totalMinutes, String dataSourceLabel, String locale,
    List<String> images, List<InstructionStep> instructions
) {}
