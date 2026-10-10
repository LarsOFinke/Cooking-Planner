package dev.cookingplanner;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.MOCK)
class ApiContractTest {
    private static final Path DATA = createDirectory();
    @Autowired WebApplicationContext context;

    private static Path createDirectory() {
        try { return Files.createTempDirectory("cooking-planner-api-"); }
        catch (IOException e) { throw new IllegalStateException(e); }
    }

    @DynamicPropertySource
    static void properties(DynamicPropertyRegistry registry) {
        registry.add("cooking-planner.data-dir", DATA::toString);
    }

    @Test
    void createRecipeAndPlanThroughHttpContract() throws Exception {
        var mvc = MockMvcBuilders.webAppContextSetup(context).build();
        String recipe = """
            {"title":"Soup","category":"Dinner","ingredients":["Tomato"],"instructions":"Simmer","prepMinutes":20}
            """;
        mvc.perform(post("/api/recipes").contentType("application/json").content(recipe))
            .andExpect(status().isCreated()).andExpect(jsonPath("$.id").value(1));
        mvc.perform(get("/api/recipes/locales"))
            .andExpect(status().isOk()).andExpect(jsonPath("$[0]").value("en"));
        mvc.perform(post("/api/recipes/import?locale=de").contentType("application/json").content("[" + recipe.replace("Soup", "Suppe") + "]"))
            .andExpect(status().isCreated()).andExpect(jsonPath("$[0].locale").value("de"));
        mvc.perform(get("/api/recipes?locale=de"))
            .andExpect(status().isOk()).andExpect(jsonPath("$[0].title").value("Suppe"));
        mvc.perform(get("/api/recipes?locale=en"))
            .andExpect(status().isOk()).andExpect(jsonPath("$[0].title").value("Soup"));
        mvc.perform(put("/api/plans").contentType("application/json")
            .content("{\"date\":\"2026-10-10\",\"mealType\":\"DINNER\",\"recipeId\":1}"))
            .andExpect(status().isOk()).andExpect(jsonPath("$.recipeTitle").value("Soup"));
        mvc.perform(get("/api/plans?from=2026-10-10&to=2026-10-10"))
            .andExpect(status().isOk()).andExpect(jsonPath("$[0].mealType").value("DINNER"));
        mvc.perform(post("/api/recipes").contentType("application/json").content("{}"))
            .andExpect(status().isBadRequest());
    }

    @AfterAll
    static void cleanUp() throws IOException {
        try (var files = Files.list(DATA)) {
            for (Path file : files.toList()) Files.deleteIfExists(file);
        }
        Files.deleteIfExists(DATA);
    }
}
