package dev.cookingplanner.recipes.services;

import dev.cookingplanner.recipes.repositories.RecipeEditRepository;
import dev.cookingplanner.recipes.repositories.RecipeRepository;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.node.ArrayNode;
import tools.jackson.databind.node.ObjectNode;

@Service
public class RecipeAdminService {
    public record EditInput(String sourceLocale, Map<String, JsonNode> translations) {}

    private static final List<String> SHARED = List.of("id", "country_code", "region_code", "continent_code",
        "category", "difficulty", "effort", "data_source", "prep_minutes", "cook_minutes", "total_minutes",
        "diet_type", "suitable_for", "image_folder", "images");
    private final RecipeRepository recipes;
    private final RecipeEditRepository edits;

    public RecipeAdminService(RecipeRepository recipes, RecipeEditRepository edits) {
        this.recipes = recipes; this.edits = edits;
    }

    public List<Map<String, Object>> list() {
        List<String> locales = recipes.locales();
        List<Map<String, Object>> result = new ArrayList<>();
        for (String id : recipes.ids()) {
            Map<String, String> names = new LinkedHashMap<>();
            for (String locale : locales) recipes.raw(locale, id).ifPresent(row -> names.put(locale, row.path("name").asString()));
            result.add(Map.of("id", id, "names", names));
        }
        return result;
    }

    /** Values remain catalog codes; labels are taken from each language's live catalog. */
    public Map<String, Map<String, List<Map<String, String>>>> options() {
        Map<String, Map<String, List<Map<String, String>>>> result = new LinkedHashMap<>();
        Map<String, String> labels = Map.of(
            "country_code", "country", "region_code", "region", "continent_code", "continent",
            "category", "category_label", "difficulty", "difficulty_label", "effort", "effort_label",
            "diet_type", "diet_type_label", "data_source", "data_source_label");
        for (String locale : recipes.locales()) {
            Map<String, Map<String, String>> choices = new LinkedHashMap<>();
            for (String key : labels.keySet()) choices.put(key, new java.util.TreeMap<>());
            choices.put("suitable_for", new java.util.TreeMap<>());
            for (JsonNode row : recipes.rawAll(locale)) {
                for (var entry : labels.entrySet()) {
                    String code = row.path(entry.getKey()).asString("");
                    if (!code.isBlank()) {
                        String label = row.path(entry.getValue()).asString("");
                        choices.get(entry.getKey()).putIfAbsent(code, label.isBlank() ? code : label);
                    }
                }
                JsonNode diets = row.path("suitable_for");
                JsonNode dietLabels = row.path("suitable_for_labels");
                for (int index = 0; index < diets.size(); index++) {
                    String code = diets.get(index).asString("");
                    if (!code.isBlank()) {
                        String label = index < dietLabels.size() ? dietLabels.get(index).asString("") : "";
                        choices.get("suitable_for").putIfAbsent(code, label.isBlank() ? code : label);
                    }
                }
            }
            Map<String, List<Map<String, String>>> localized = new LinkedHashMap<>();
            choices.forEach((key, values) -> localized.put(key, values.entrySet().stream()
                .map(entry -> Map.of("value", entry.getKey(), "label", entry.getValue()))
                .sorted(java.util.Comparator.comparing(option -> option.get("label"))).toList()));
            result.put(locale, localized);
        }
        return result;
    }

    public Map<String, Object> get(String id) {
        Map<String, JsonNode> translations = new LinkedHashMap<>();
        boolean found = false;
        for (String locale : recipes.locales()) {
            JsonNode row = recipes.raw(locale, id).orElse(null);
            translations.put(locale, row);
            found |= row != null;
        }
        if (!found) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Recipe not found");
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("id", id);
        response.put("translations", translations);
        return response;
    }

    public synchronized Map<String, Object> save(String id, EditInput input, boolean create) {
        if (id == null || !id.matches("[a-z0-9]+(?:-[a-z0-9]+)*") || id.length() > 100)
            throw bad("Recipe ID must use lowercase letters, numbers and hyphens");
        boolean exists = recipes.ids().contains(id);
        if (create && exists) throw new ResponseStatusException(HttpStatus.CONFLICT, "Recipe ID already exists");
        if (create && edits.snapshot().deleted().contains(id))
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Deleted recipe IDs cannot be reused");
        if (!create && !exists) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Recipe not found");
        List<String> locales = recipes.locales();
        if (locales.isEmpty() || input == null || input.sourceLocale() == null ||
            !locales.contains(input.sourceLocale()) || input.translations() == null ||
            !input.translations().keySet().equals(new HashSet<>(locales))) {
            throw bad("Choose a source language and provide a translation or intentional omission for every language");
        }
        JsonNode source = input.translations().get(input.sourceLocale());
        if (source == null || !source.isObject() || !id.equals(source.path("id").asString()))
            throw bad("Source recipe must use the selected recipe ID");
        validateShared(source);
        Map<String, JsonNode> synchronizedRows = new LinkedHashMap<>();
        for (String locale : locales) {
            JsonNode translated = input.translations().get(locale);
            if (translated == null || translated.isNull()) {
                if (locale.equals(input.sourceLocale())) throw bad("The source language cannot be omitted");
                synchronizedRows.put(locale, null);
                continue;
            }
            if (!translated.isObject()) throw bad("Translation for " + locale + " must be a JSON object");
            synchronizedRows.put(locale, synchronizeRow(source, translated, locale));
        }
        edits.upsert(id, synchronizedRows);
        return get(id);
    }

    public synchronized void delete(String id) {
        if (!recipes.ids().contains(id)) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Recipe not found");
        edits.delete(id);
    }

    private ObjectNode synchronizeRow(JsonNode source, JsonNode translated, String locale) {
        ObjectNode row = (ObjectNode) translated.deepCopy();
        for (String key : SHARED) row.set(key, source.path(key).deepCopy());
        String name = row.path("name").asString().trim();
        if (name.isEmpty() || name.length() > 180) throw bad("Recipe name is required for " + locale);
        Map<String, String> ingredientNames = new HashMap<>();
        for (JsonNode ingredient : translated.path("ingredients")) {
            ingredientNames.put(ingredient.path("ingredient_id").asString(), ingredient.path("name").asString().trim());
        }
        ArrayNode ingredients = row.arrayNode();
        for (JsonNode ingredient : source.path("ingredients")) {
            String ingredientId = ingredient.path("ingredient_id").asString();
            String translatedName = ingredientNames.getOrDefault(ingredientId, "");
            if (translatedName.isEmpty() || translatedName.length() > 180)
                throw bad("Translate ingredient " + ingredientId + " for " + locale + " or omit that language");
            ObjectNode updated = (ObjectNode) ingredient.deepCopy();
            updated.put("name", translatedName);
            ingredients.add(updated);
        }
        row.set("ingredients", ingredients);
        return row;
    }

    private void validateShared(JsonNode row) {
        for (String key : SHARED) {
            if (row.path(key).isMissingNode() || row.path(key).isNull()) throw bad("Missing field: " + key);
        }
        for (String key : List.of("category", "difficulty", "effort", "data_source", "diet_type")) {
            if (row.path(key).asString().isBlank()) throw bad("Missing field: " + key);
        }
        for (String key : List.of("prep_minutes", "cook_minutes", "total_minutes")) {
            JsonNode minutes = row.path(key);
            if (!minutes.isIntegralNumber() || minutes.asInt() < 0 || minutes.asInt() > 1440)
                throw bad(key + " must be between 0 and 1440");
        }
        if (!row.path("suitable_for").isArray() || !row.path("images").isArray())
            throw bad("suitable_for and images must be arrays");
        String id = row.path("id").asString();
        if (!row.path("image_folder").asString().equals("recipe_images/" + id) ||
            row.path("images").size() > 3) throw bad("Invalid recipe image folder or image count");
        for (JsonNode image : row.path("images")) {
            if (!image.isString() ||
                !image.asString().matches("recipe_images/" + id + "/image_0[1-3]\\.(webp|png|jpg|jpeg)")) {
                throw bad("Images must be numbered files in this recipe's image folder");
            }
        }
        JsonNode ingredients = row.path("ingredients");
        if (!ingredients.isArray() || ingredients.isEmpty() || ingredients.size() > 100)
            throw bad("A recipe needs 1 to 100 ingredients");
        Set<String> ingredientIds = new HashSet<>();
        for (JsonNode ingredient : ingredients) {
            String ingredientId = ingredient.path("ingredient_id").asString();
            JsonNode amount = ingredient.path("amount");
            if (!ingredientId.matches("[a-z0-9]+(?:-[a-z0-9]+)*") || !ingredientIds.add(ingredientId) ||
                !amount.isNumber() || amount.decimalValue().compareTo(BigDecimal.ZERO) <= 0 ||
                !List.of("g", "ml", "pcs").contains(ingredient.path("unit").asString())) {
                throw bad("Ingredients need unique IDs, positive amounts and g, ml or pcs units");
            }
        }
    }

    private ResponseStatusException bad(String message) {
        return new ResponseStatusException(HttpStatus.BAD_REQUEST, message);
    }
}
