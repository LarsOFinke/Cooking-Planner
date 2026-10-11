package dev.cookingplanner;

import static org.junit.jupiter.api.Assertions.*;

import dev.cookingplanner.plans.dtos.MealPlanInput;
import dev.cookingplanner.plans.dtos.MealType;
import dev.cookingplanner.plans.repositories.MealPlanRepository;
import dev.cookingplanner.plans.services.MealPlanService;
import dev.cookingplanner.plans.services.ShoppingService;
import dev.cookingplanner.recipes.mappers.CatalogMapper;
import dev.cookingplanner.recipes.repositories.RecipeEditRepository;
import dev.cookingplanner.recipes.repositories.RecipeRepository;
import dev.cookingplanner.shared.JsonFileStore;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.web.server.ResponseStatusException;
import tools.jackson.databind.ObjectMapper;

class CatalogAndPlanTest {
    @TempDir Path directory;

    private RecipeRepository repository(Path catalogDirectory, ObjectMapper json) {
        return new RecipeRepository(catalogDirectory.toString(), json, new CatalogMapper(),
            new RecipeEditRepository(new JsonFileStore(directory.toString(), json)));
    }

    static Path catalogs() {
        Path local = Path.of("data");
        return Files.isDirectory(local) ? local : Path.of("..", "data");
    }

    @Test
    void sourceCatalogsShareIdsAndTranslateDetails() {
        var repository = repository(catalogs(), new ObjectMapper());
        assertEquals(List.of("de", "en"), repository.locales());
        assertEquals(586, repository.findAll("en").size());
        assertEquals(586, repository.findAll("de").size());
        var english = repository.findById("en", "dz-algerischer-couscous").orElseThrow();
        var german = repository.findById("de", english.id()).orElseThrow();
        assertEquals("Algerian Couscous", english.name());
        assertEquals("Algerischer Couscous", german.name());
        assertEquals(english.ingredients().getFirst().amount(), german.ingredients().getFirst().amount());
        assertEquals(english.images(), german.images());
        assertEquals(586, repository.info("en").recipeCount());
        assertFalse(english.instructions().isEmpty());
        assertEquals(1, english.instructions().getFirst().step());
        assertNotEquals(english.instructions().getFirst().text(), german.instructions().getFirst().text());
    }

    @Test
    void plansSurviveRestartTranslateAndScaleShoppingAmounts() {
        var json = new ObjectMapper();
        var recipes = repository(catalogs(), json);
        var plans = new MealPlanRepository(new JsonFileStore(directory.toString(), json));
        var service = new MealPlanService(plans, recipes);
        var day = LocalDate.parse("2026-10-10");
        var input = new MealPlanInput(day, MealType.DINNER, "dz-algerischer-couscous", 2);
        service.save(input);
        var reopened = new MealPlanRepository(new JsonFileStore(directory.toString(), new ObjectMapper()));
        assertEquals("Algerischer Couscous", new MealPlanService(reopened, recipes).list(day, day, "de").getFirst().recipeTitle());
        var ingredient = recipes.findById("en", input.recipeId()).orElseThrow().ingredients().getFirst();
        var shopping = new ShoppingService(new MealPlanService(reopened, recipes), recipes).list(day, day, "en");
        assertEquals(ingredient.amount().multiply(java.math.BigDecimal.valueOf(2)),
            shopping.stream().filter(item -> item.ingredientId().equals(ingredient.ingredientId())).findFirst().orElseThrow().amount());
        assertTrue(Files.exists(directory.resolve("plans.json")));
    }

    @Test
    void replacingSlotKeepsIdAndRemovalClearsShoppingList() {
        var json = new ObjectMapper();
        var recipes = repository(catalogs(), json);
        var plans = new MealPlanRepository(new JsonFileStore(directory.toString(), json));
        var service = new MealPlanService(plans, recipes);
        var shopping = new ShoppingService(service, recipes);
        var day = LocalDate.parse("2026-10-10");
        var first = service.save(new MealPlanInput(day, MealType.DINNER, "dz-algerischer-couscous", 2));
        var replaced = service.save(new MealPlanInput(day, MealType.DINNER, "dz-algerischer-couscous", 3));
        assertEquals(first.id(), replaced.id());
        assertEquals(1, service.list(day, day, "en").size());
        var ingredient = recipes.findById("en", first.recipeId()).orElseThrow().ingredients().getFirst();
        assertEquals(ingredient.amount().multiply(java.math.BigDecimal.valueOf(3)),
            shopping.list(day, day, "en").stream()
                .filter(item -> item.ingredientId().equals(ingredient.ingredientId()))
                .findFirst().orElseThrow().amount());
        service.delete(first.id());
        assertTrue(shopping.list(day, day, "en").isEmpty());
        assertThrows(ResponseStatusException.class, () -> service.delete(first.id()));
    }

    @Test
    void invalidDatesAndUnknownRecipesAreRejected() {
        var json = new ObjectMapper();
        var recipes = repository(catalogs(), json);
        var service = new MealPlanService(new MealPlanRepository(new JsonFileStore(directory.toString(), json)), recipes);
        var day = LocalDate.parse("2026-10-10");
        assertThrows(ResponseStatusException.class, () -> service.list(day, day.minusDays(1), "en"));
        assertThrows(ResponseStatusException.class, () -> service.list(day, day.plusDays(63), "en"));
        assertThrows(ResponseStatusException.class,
            () -> service.save(new MealPlanInput(day, MealType.DINNER, "missing", 1)));
        assertTrue(recipes.findById("de", "missing").isEmpty());
    }

    @Test
    void mismatchedCatalogMetadataFailsWithoutTouchingSource() throws Exception {
        var source = Files.readString(catalogs().resolve("recipes_en.json"));
        var damaged = source.replaceFirst("\\\"schema_version\\\": \\\"1\\.2\\.0\\\"", "\"schema_version\": \"9.0.0\"");
        Files.writeString(directory.resolve("recipes_en.json"), damaged);
        var repository = repository(directory, new ObjectMapper());
        assertThrows(IllegalStateException.class, () -> repository.findAll("en"));
        assertEquals(source, Files.readString(catalogs().resolve("recipes_en.json")));
    }
}
