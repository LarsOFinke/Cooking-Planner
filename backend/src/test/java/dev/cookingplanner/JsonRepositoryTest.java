package dev.cookingplanner;

import static org.junit.jupiter.api.Assertions.*;

import dev.cookingplanner.plans.dtos.MealPlanInput;
import dev.cookingplanner.plans.dtos.MealType;
import dev.cookingplanner.plans.repositories.MealPlanRepository;
import dev.cookingplanner.recipes.dtos.RecipeInput;
import dev.cookingplanner.recipes.repositories.RecipeRepository;
import dev.cookingplanner.recipes.services.RecipeService;
import dev.cookingplanner.shared.JsonFileStore;
import jakarta.validation.Validation;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.web.server.ResponseStatusException;
import tools.jackson.databind.ObjectMapper;

class JsonRepositoryTest {
    @TempDir Path directory;

    @Test
    void recipesAndPlansSurviveRepositoryRestart() throws Exception {
        var store = new JsonFileStore(directory.toString(), new ObjectMapper());
        var recipes = new RecipeRepository(store);
        var plans = new MealPlanRepository(store);
        long recipeId = recipes.create("en", new RecipeInput("Soup", "Dinner", List.of("Tomato"), "Simmer", 20)).id();
        plans.save(new MealPlanInput(LocalDate.parse("2026-10-10"), MealType.DINNER, recipeId));

        var reopened = new JsonFileStore(directory.toString(), new ObjectMapper());
        assertEquals("Soup", new RecipeRepository(reopened).findById(recipeId).orElseThrow().title());
        assertEquals(recipeId, new MealPlanRepository(reopened)
            .findBetween(LocalDate.parse("2026-10-10"), LocalDate.parse("2026-10-10")).getFirst().recipeId());
        assertTrue(Files.exists(directory.resolve("recipes_en.json")));
        assertTrue(Files.exists(directory.resolve("plans.json")));
    }

    @Test
    void invalidBatchImportDoesNotChangeExistingRecipes() {
        var store = new JsonFileStore(directory.toString(), new ObjectMapper());
        var recipes = new RecipeRepository(store);
        try (var factory = Validation.buildDefaultValidatorFactory()) {
            var service = new RecipeService(recipes, factory.getValidator(), new MealPlanRepository(store));
            var valid = new RecipeInput("Soup", "Dinner", List.of("Tomato"), "Simmer", 20);
            var invalid = new RecipeInput("", "Dinner", List.of("Tomato"), "Simmer", 20);
            assertThrows(ResponseStatusException.class, () -> service.importRecipes("en", List.of(valid, invalid)));
            assertTrue(recipes.findAll("en").isEmpty());
        }
    }

    @Test
    void catalogsStaySeparateAndIdsRemainUnique() {
        var recipes = new RecipeRepository(new JsonFileStore(directory.toString(), new ObjectMapper()));
        long englishId = recipes.create("en", new RecipeInput("Soup", "Dinner", List.of("Tomato"), "Simmer", 20)).id();
        long germanId = recipes.create("de", new RecipeInput("Suppe", "Abendessen", List.of("Tomate"), "Kochen", 20)).id();
        assertNotEquals(englishId, germanId);
        assertEquals(List.of("de", "en"), recipes.locales());
        assertEquals("Soup", recipes.findAll("en").getFirst().title());
        assertEquals("Suppe", recipes.findAll("de").getFirst().title());
    }

    @Test
    void legacyEnglishCatalogIsReadAndCopiedOnFirstWrite() throws Exception {
        Files.writeString(directory.resolve("recipes.json"), """
            [{"id":7,"title":"Old soup","category":"Dinner","ingredients":["Tomato"],"instructions":"Simmer","prepMinutes":20}]
            """);
        var recipes = new RecipeRepository(new JsonFileStore(directory.toString(), new ObjectMapper()));
        assertEquals("Old soup", recipes.findAll("en").getFirst().title());
        assertEquals(8, recipes.create("en", new RecipeInput("New soup", "Dinner", List.of("Tomato"), "Simmer", 20)).id());
        assertTrue(Files.exists(directory.resolve("recipes_en.json")));
        assertEquals(2, recipes.findAll("en").size());
    }
}
