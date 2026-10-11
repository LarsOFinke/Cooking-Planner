package dev.cookingplanner;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import static org.junit.jupiter.api.Assertions.*;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
import dev.cookingplanner.recipes.repositories.RecipeRepository;
import dev.cookingplanner.recipes.services.RecipeAdminService.EditInput;
import org.springframework.jdbc.core.JdbcTemplate;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ObjectNode;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.MOCK)
class ApiContractTest {
    private static final Path DATA = createDirectory();
    @Autowired WebApplicationContext context;
    @Autowired RecipeRepository recipes;
    @Autowired ObjectMapper json;
    @Autowired JdbcTemplate jdbc;

    private static Path createDirectory() {
        try {
            Path directory = Files.createTempDirectory("cooking-planner-api-");
            Files.writeString(directory.resolve("shopping.json"),
                "{\"version\":1,\"weeks\":{\"2026-10-05\":{\"plans\":[],\"excluded\":[]," +
                "\"custom\":[],\"checked\":[],\"prices\":{\"couscous:g\":\"2.50\"}}}}");
            return directory;
        }
        catch (IOException e) { throw new IllegalStateException(e); }
    }

    @DynamicPropertySource
    static void properties(DynamicPropertyRegistry registry) {
        registry.add("cooking-planner.data-dir", DATA::toString);
        registry.add("cooking-planner.catalog-dir", () -> CatalogAndPlanTest.catalogs().toAbsolutePath().toString());
    }

    @Test
    void localePlansAndShoppingWorkThroughHttpContract() throws Exception {
        var mvc = MockMvcBuilders.webAppContextSetup(context).build();
        mvc.perform(get("/api/health"))
            .andExpect(status().isOk()).andExpect(jsonPath("$.status").value("ok"))
            .andExpect(jsonPath("$.instanceToken").exists());
        mvc.perform(get("/api/recipes/locales"))
            .andExpect(status().isOk()).andExpect(jsonPath("$[0]").value("de"));
        mvc.perform(get("/api/recipes?locale=en"))
            .andExpect(status().isOk()).andExpect(jsonPath("$[0].name").exists());
        mvc.perform(get("/api/recipes/dz-algerischer-couscous?locale=de"))
            .andExpect(status().isOk()).andExpect(jsonPath("$.name").value("Algerischer Couscous"));
        mvc.perform(get("/api/recipes/info?locale=en"))
            .andExpect(status().isOk()).andExpect(jsonPath("$.recipeCount").value(586));
        mvc.perform(get("/api/admin/recipes"))
            .andExpect(status().isOk()).andExpect(jsonPath("$[0].id").exists());
        mvc.perform(get("/api/admin/recipes/options"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.en.category[?(@.value == 'main')].label").isNotEmpty())
            .andExpect(jsonPath("$.de.category[?(@.value == 'main')].label").isNotEmpty())
            .andExpect(jsonPath("$.en.suitable_for[?(@.value == 'omnivore')].label").isNotEmpty());
        mvc.perform(get("/api/admin/recipes/dz-algerischer-couscous"))
            .andExpect(status().isOk()).andExpect(jsonPath("$.translations.en.name").value("Algerian Couscous"));
        mvc.perform(put("/api/plans").contentType("application/json")
            .content("{\"date\":\"2026-10-10\",\"mealType\":\"DINNER\",\"recipeId\":\"dz-algerischer-couscous\",\"servings\":2}"))
            .andExpect(status().isOk()).andExpect(jsonPath("$.servings").value(2));
        mvc.perform(get("/api/plans?from=2026-10-10&to=2026-10-10&locale=de"))
            .andExpect(status().isOk()).andExpect(jsonPath("$[0].recipeTitle").value("Algerischer Couscous"));
        mvc.perform(get("/api/plans/shopping?from=2026-10-10&to=2026-10-10&locale=en"))
            .andExpect(status().isOk()).andExpect(jsonPath("$[0].amount").exists());
        mvc.perform(put("/api/plans").contentType("application/json").content("{}"))
            .andExpect(status().isBadRequest());
    }

    @Test
    void adminCanCreateInOneLanguageAndDeleteThroughHttp() throws Exception {
        var mvc = MockMvcBuilders.webAppContextSetup(context).build();
        String id = "test-admin-api";
        ObjectNode row = (ObjectNode) recipes.raw("en", "dz-algerischer-couscous").orElseThrow().deepCopy();
        row.put("id", id);
        row.put("name", "Admin API dish");
        row.put("image_folder", "recipe_images/" + id);
        row.putArray("images");
        Map<String, JsonNode> translations = new LinkedHashMap<>();
        translations.put("en", row);
        translations.put("de", null);
        mvc.perform(post("/api/admin/recipes/{id}", id).contentType("application/json")
            .content(json.writeValueAsBytes(new EditInput("en", translations))))
            .andExpect(status().isCreated()).andExpect(jsonPath("$.translations.en.name").value("Admin API dish"));
        mvc.perform(post("/api/admin/recipes/{id}", id).contentType("application/json")
            .content(json.writeValueAsBytes(new EditInput("en", translations))))
            .andExpect(status().isConflict()).andExpect(jsonPath("$.message").value("Recipe ID already exists"));
        mvc.perform(get("/api/recipes/{id}?locale=en", id))
            .andExpect(status().isOk()).andExpect(jsonPath("$.name").value("Admin API dish"));
        mvc.perform(get("/api/recipes/{id}?locale=de", id)).andExpect(status().isNotFound());
        mvc.perform(delete("/api/admin/recipes/{id}", id)).andExpect(status().isNoContent());
        mvc.perform(get("/api/recipes/{id}?locale=en", id)).andExpect(status().isNotFound());
    }

    @Test
    void localizedIngredientsAndLegacyPricesLiveInNormalizedSqliteTables() throws Exception {
        var mvc = MockMvcBuilders.webAppContextSetup(context).build();
        mvc.perform(get("/api/ingredients?locale=en&q=Carrot"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$[?(@.id == 'karotte')].translations.de").value("Karotte"));
        mvc.perform(get("/api/ingredients?locale=de&q=Karotte"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$[?(@.id == 'karotte')].translations.en").value("Carrot"));
        mvc.perform(post("/api/ingredients").contentType("application/json")
            .content("{\"id\":\"custom-pantry-test\",\"locale\":\"en\",\"name\":\"Pantry item\"}"))
            .andExpect(status().isCreated());
        mvc.perform(post("/api/ingredients").contentType("application/json")
            .content("{\"id\":\"custom-pantry-test\",\"locale\":\"de\",\"name\":\"Vorrat\"}"))
            .andExpect(status().isCreated());
        mvc.perform(get("/api/ingredients?locale=de&q=Vorrat"))
            .andExpect(status().isOk()).andExpect(jsonPath("$[0].translations.en").value("Pantry item"));
        mvc.perform(get("/api/ingredients/prices?week=2026-10-05"))
            .andExpect(status().isOk()).andExpect(jsonPath("$['couscous:g']").value("2.50"));
        mvc.perform(put("/api/ingredients/couscous/prices?week=2026-10-05&unit=g")
            .contentType("application/json").content("{\"price\":\"3,75\"}"))
            .andExpect(status().isOk());
        mvc.perform(get("/api/ingredients/prices?week=2026-10-05"))
            .andExpect(status().isOk()).andExpect(jsonPath("$['couscous:g']").value("3.75"));
        mvc.perform(put("/api/ingredients/couscous/prices?week=2026-10-05&unit=g")
            .contentType("application/json").content("{\"price\":\"-1\"}"))
            .andExpect(status().isBadRequest());
        assertEquals(1, jdbc.queryForObject("SELECT count(*) FROM ingredient WHERE id='karotte'", Integer.class));
        assertEquals(2, jdbc.queryForObject(
            "SELECT count(*) FROM ingredient_translation WHERE ingredient_id='karotte'", Integer.class));
        assertEquals(1, jdbc.queryForObject(
            "SELECT count(*) FROM ingredient_price WHERE ingredient_id='couscous'", Integer.class));
        assertEquals(1, jdbc.queryForObject("PRAGMA foreign_keys", Integer.class));
        assertTrue(Files.readString(DATA.resolve("shopping.json")).contains("2.50"));
        mvc.perform(delete("/api/ingredients/prices?week=2026-10-05"))
            .andExpect(status().isOk());
        assertEquals(0, jdbc.queryForObject(
            "SELECT count(*) FROM ingredient_price WHERE week_start='2026-10-05'", Integer.class));
    }

    @Test
    void ingredientAdminEditsTranslationsAndProtectsUsedIngredients() throws Exception {
        var mvc = MockMvcBuilders.webAppContextSetup(context).build();
        mvc.perform(put("/api/admin/ingredients/test-admin-spice").contentType("application/json")
            .content("{\"translations\":{\"en\":\"Spice blend\",\"de\":\"Gewürzmischung\"}}"))
            .andExpect(status().isOk()).andExpect(jsonPath("$.translations.de").value("Gewürzmischung"));
        mvc.perform(get("/api/admin/ingredients?q=test-admin-spice"))
            .andExpect(status().isOk()).andExpect(jsonPath("$[0].id").value("test-admin-spice"));
        mvc.perform(put("/api/admin/ingredients/test-admin-spice").contentType("application/json")
            .content("{\"translations\":{\"en\":\"New blend\",\"de\":\"\"}}"))
            .andExpect(status().isOk()).andExpect(jsonPath("$.translations.en").value("New blend"))
            .andExpect(jsonPath("$.translations.de").doesNotExist());
        mvc.perform(get("/api/ingredients?locale=en&q=New blend"))
            .andExpect(status().isOk()).andExpect(jsonPath("$[0].id").value("test-admin-spice"));
        mvc.perform(put("/api/admin/ingredients/karotte").contentType("application/json")
            .content("{\"translations\":{\"en\":\"Carrot\",\"de\":\"\"}}"))
            .andExpect(status().isConflict());
        mvc.perform(delete("/api/admin/ingredients/karotte")).andExpect(status().isConflict());
        mvc.perform(put("/api/ingredients/test-admin-spice/prices?week=2026-10-12&unit=g")
            .contentType("application/json").content("{\"price\":\"1.25\"}"))
            .andExpect(status().isOk());
        mvc.perform(delete("/api/admin/ingredients/test-admin-spice")).andExpect(status().isConflict());
        mvc.perform(put("/api/ingredients/test-admin-spice/prices?week=2026-10-12&unit=g")
            .contentType("application/json").content("{\"price\":\"\"}"))
            .andExpect(status().isOk());
        mvc.perform(delete("/api/admin/ingredients/test-admin-spice")).andExpect(status().isOk());
        mvc.perform(get("/api/admin/ingredients/test-admin-spice")).andExpect(status().isNotFound());
    }

    @AfterAll
    static void cleanUp() throws IOException {
        try (var files = Files.list(DATA)) {
            for (Path file : files.toList()) Files.deleteIfExists(file);
        }
        Files.deleteIfExists(DATA);
    }
}
