package dev.cookingplanner.recipes.mappers;

import dev.cookingplanner.recipes.entities.CatalogInfo;
import dev.cookingplanner.recipes.entities.Ingredient;
import dev.cookingplanner.recipes.entities.InstructionStep;
import dev.cookingplanner.recipes.entities.Recipe;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import org.springframework.stereotype.Component;
import tools.jackson.databind.JsonNode;

@Component
public class CatalogMapper {
    private String value(JsonNode node, String field) {
        JsonNode child = node.path(field);
        return child.isMissingNode() || child.isNull() ? "" : child.asString();
    }
    private List<String> strings(JsonNode node, String field) {
        List<String> values = new ArrayList<>();
        for (JsonNode item : node.path(field)) values.add(item.asString());
        return List.copyOf(values);
    }
    public Recipe recipe(JsonNode row, String locale) {
        List<Ingredient> ingredients = new ArrayList<>();
        for (JsonNode item : row.path("ingredients")) {
            ingredients.add(new Ingredient(value(item, "name"), value(item, "ingredient_id"),
                new BigDecimal(value(item, "amount")), value(item, "unit")));
        }
        List<InstructionStep> steps = new ArrayList<>();
        for (JsonNode item : row.path("instructions").path("steps")) {
            steps.add(new InstructionStep(item.path("step").asInt(), value(item, "text"),
                strings(item, "ingredient_ids")));
        }
        return new Recipe(value(row, "id"), value(row, "name"), value(row, "country"), value(row, "country_code"),
            value(row, "region"), value(row, "continent"), value(row, "category"), value(row, "category_label"),
            value(row, "difficulty"), value(row, "difficulty_label"), value(row, "effort"), value(row, "effort_label"),
            value(row, "diet_type"), value(row, "diet_type_label"), strings(row, "suitable_for"),
            strings(row, "suitable_for_labels"), List.copyOf(ingredients), row.path("prep_minutes").asInt(),
            row.path("cook_minutes").asInt(), row.path("total_minutes").asInt(), value(row, "data_source_label"), locale,
            strings(row, "images"), List.copyOf(steps));
    }
    public CatalogInfo info(JsonNode metadata, String locale, int actualCount) {
        return new CatalogInfo(locale, value(metadata, "dataset"), actualCount,
            metadata.path("country_count").asInt(), metadata.path("region_count").asInt(),
            value(metadata, "quantity_note"), value(metadata, "diet_note"),
            value(metadata, "origin_note"), value(metadata, "quality"));
    }
}
