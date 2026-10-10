package dev.cookingplanner.recipes.dtos;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.util.List;

public record RecipeInput(
    @NotBlank @Size(max = 120) String title,
    @NotBlank @Size(max = 60) String category,
    @NotEmpty @Size(max = 100) List<@NotBlank @Size(max = 300) String> ingredients,
    @NotBlank @Size(max = 10000) String instructions,
    @NotNull @Min(0) Integer prepMinutes
) {}
