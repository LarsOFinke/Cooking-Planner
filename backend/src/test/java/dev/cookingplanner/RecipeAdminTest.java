package dev.cookingplanner;

import static org.junit.jupiter.api.Assertions.*;

import dev.cookingplanner.plans.dtos.MealPlanInput;
import dev.cookingplanner.plans.dtos.MealType;
import dev.cookingplanner.plans.repositories.MealPlanRepository;
import dev.cookingplanner.plans.services.MealPlanService;
import dev.cookingplanner.recipes.mappers.CatalogMapper;
import dev.cookingplanner.recipes.repositories.RecipeEditRepository;
import dev.cookingplanner.recipes.repositories.RecipeRepository;
import dev.cookingplanner.recipes.services.RecipeAdminService;
import dev.cookingplanner.recipes.services.RecipeAdminService.EditInput;
import dev.cookingplanner.shared.JsonFileStore;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.util.LinkedHashMap;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.web.server.ResponseStatusException;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ObjectNode;

class RecipeAdminTest {
    @TempDir Path directory;

    private RecipeRepository repository(Path catalogs, ObjectMapper json, RecipeEditRepository edits) {
        return new RecipeRepository(catalogs.toString(), json, new CatalogMapper(), edits);
    }

    @Test
    void editCreateOmitTranslateAndDeleteSurviveRestartWithoutChangingCatalogs() throws Exception {
        Path catalogs = Files.createDirectory(directory.resolve("catalogs"));
        Path userData = Files.createDirectory(directory.resolve("user"));
        byte[] english = Files.readAllBytes(CatalogAndPlanTest.catalogs().resolve("recipes_en.json"));
        byte[] german = Files.readAllBytes(CatalogAndPlanTest.catalogs().resolve("recipes_de.json"));
        Files.write(catalogs.resolve("recipes_en.json"), english);
        Files.write(catalogs.resolve("recipes_de.json"), german);
        ObjectMapper json = new ObjectMapper();
        RecipeEditRepository edits = new RecipeEditRepository(new JsonFileStore(userData.toString(), json));
        RecipeRepository recipes = repository(catalogs, json, edits);
        RecipeAdminService admin = new RecipeAdminService(recipes, edits);
        String originalId = "dz-algerischer-couscous";
        ObjectNode en = (ObjectNode) recipes.raw("en", originalId).orElseThrow().deepCopy();
        ObjectNode de = (ObjectNode) recipes.raw("de", originalId).orElseThrow().deepCopy();
        ((ObjectNode) en.path("ingredients").get(0)).put("amount", 125);
        en.put("prep_minutes", 35);
        admin.save(originalId, new EditInput("en", Map.of("en", en, "de", de)), false);
        assertEquals(125, recipes.raw("de", originalId).orElseThrow().path("ingredients").get(0).path("amount").asInt());
        assertEquals(35, recipes.findById("de", originalId).orElseThrow().prepMinutes());
        assertEquals("Algerischer Couscous", recipes.findById("de", originalId).orElseThrow().name());

        String newId = "sample-admin-dish";
        ObjectNode newEnglish = (ObjectNode) en.deepCopy();
        newEnglish.put("id", newId);
        newEnglish.put("name", "Sample admin dish");
        newEnglish.put("image_folder", "recipe_images/" + newId);
        newEnglish.putArray("images");
        Map<String, JsonNode> translations = new LinkedHashMap<>();
        translations.put("en", newEnglish);
        translations.put("de", null);
        admin.save(newId, new EditInput("en", translations), true);
        assertTrue(recipes.findById("en", newId).isPresent());
        assertTrue(recipes.findById("de", newId).isEmpty());
        assertEquals(587, recipes.info("en").recipeCount());
        assertEquals(586, recipes.info("de").recipeCount());

        ObjectNode newGerman = (ObjectNode) de.deepCopy();
        newGerman.put("id", newId);
        newGerman.put("name", "Admin-Beispielgericht");
        translations.put("de", newGerman);
        admin.save(newId, new EditInput("en", translations), false);
        assertEquals("Admin-Beispielgericht", recipes.findById("de", newId).orElseThrow().name());

        MealPlanService plans = new MealPlanService(
            new MealPlanRepository(new JsonFileStore(userData.toString(), json)), recipes);
        LocalDate day = LocalDate.parse("2026-10-11");
        plans.save(new MealPlanInput(day, MealType.DINNER, newId, 2));

        RecipeEditRepository reopenedEdits = new RecipeEditRepository(new JsonFileStore(userData.toString(), new ObjectMapper()));
        RecipeRepository reopened = repository(catalogs, new ObjectMapper(), reopenedEdits);
        assertTrue(reopened.findById("de", newId).isPresent());
        new RecipeAdminService(reopened, reopenedEdits).delete(newId);
        assertTrue(reopened.findById("en", newId).isEmpty());
        assertTrue(reopened.findById("de", newId).isEmpty());
        MealPlanService reopenedPlans = new MealPlanService(
            new MealPlanRepository(new JsonFileStore(userData.toString(), new ObjectMapper())), reopened);
        assertEquals(newId, reopenedPlans.list(day, day, "en").getFirst().recipeId());
        assertEquals("Missing recipe", reopenedPlans.list(day, day, "en").getFirst().recipeTitle());
        assertThrows(ResponseStatusException.class,
            () -> new RecipeAdminService(reopened, reopenedEdits)
                .save(newId, new EditInput("en", translations), true));
        assertArrayEquals(english, Files.readAllBytes(catalogs.resolve("recipes_en.json")));
        assertArrayEquals(german, Files.readAllBytes(catalogs.resolve("recipes_de.json")));
    }

    @Test
    void missingIngredientTranslationDoesNotWriteEdits() throws Exception {
        ObjectMapper json = new ObjectMapper();
        RecipeEditRepository edits = new RecipeEditRepository(new JsonFileStore(directory.toString(), json));
        RecipeRepository recipes = repository(CatalogAndPlanTest.catalogs(), json, edits);
        RecipeAdminService admin = new RecipeAdminService(recipes, edits);
        String id = "dz-algerischer-couscous";
        ObjectNode en = (ObjectNode) recipes.raw("en", id).orElseThrow().deepCopy();
        ObjectNode de = (ObjectNode) recipes.raw("de", id).orElseThrow().deepCopy();
        ((ObjectNode) en.path("ingredients").get(0)).put("ingredient_id", "new-ingredient");
        assertThrows(ResponseStatusException.class,
            () -> admin.save(id, new EditInput("en", Map.of("en", en, "de", de)), false));
        assertFalse(Files.exists(directory.resolve("recipe-edits.json")));
        assertEquals("couscous", recipes.raw("en", id).orElseThrow().path("ingredients").get(0)
            .path("ingredient_id").asString());
    }

    @Test
    void unsupportedEditFileIsPreserved() throws Exception {
        Path file = directory.resolve("recipe-edits.json");
        String future = "{\"version\":2,\"upserts\":{},\"deleted\":[]}";
        Files.writeString(file, future);
        ObjectMapper json = new ObjectMapper();
        RecipeEditRepository edits = new RecipeEditRepository(new JsonFileStore(directory.toString(), json));
        RecipeRepository recipes = repository(CatalogAndPlanTest.catalogs(), json, edits);
        assertThrows(IllegalStateException.class, () -> recipes.findAll("en"));
        assertEquals(future, Files.readString(file));
    }
}
