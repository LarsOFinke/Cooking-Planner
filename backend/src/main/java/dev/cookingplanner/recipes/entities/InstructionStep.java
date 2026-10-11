package dev.cookingplanner.recipes.entities;

import java.util.List;

public record InstructionStep(int step, String text, List<String> ingredientIds) {}
