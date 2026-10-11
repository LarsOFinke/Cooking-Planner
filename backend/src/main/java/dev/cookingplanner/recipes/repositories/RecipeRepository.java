package dev.cookingplanner.recipes.repositories;

import dev.cookingplanner.recipes.RecipeLocale;
import dev.cookingplanner.recipes.entities.CatalogInfo;
import dev.cookingplanner.recipes.entities.Recipe;
import dev.cookingplanner.recipes.mappers.CatalogMapper;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.FileTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Repository;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

@Repository
public class RecipeRepository {
    private record Catalog(FileTime modified, long editRevision, List<Recipe> recipes,
        Map<String, Recipe> byId, Map<String, JsonNode> rawById, CatalogInfo info) {}
    private final Path directory;
    private final ObjectMapper json;
    private final CatalogMapper mapper;
    private final RecipeEditRepository edits;
    private final Map<String, Catalog> cache = new HashMap<>();

    public RecipeRepository(@Value("${cooking-planner.catalog-dir}") String directory, ObjectMapper json,
        CatalogMapper mapper, RecipeEditRepository edits) {
        this.directory = Path.of(directory).toAbsolutePath(); this.json = json; this.mapper = mapper; this.edits = edits;
    }
    public List<String> locales() {
        if (!Files.isDirectory(directory)) return List.of();
        try (var paths = Files.list(directory)) {
            return paths.map(path -> path.getFileName().toString())
                .filter(name -> name.matches("recipes_[a-z]{2}\\.json"))
                .map(name -> name.substring(8, 10)).sorted().toList();
        } catch (IOException e) { throw new IllegalStateException("Could not list recipe catalogs", e); }
    }
    private synchronized Catalog catalog(String language) {
        String locale = RecipeLocale.normalize(language);
        Path file = directory.resolve("recipes_" + locale + ".json");
        if (!Files.isRegularFile(file)) throw new IllegalArgumentException("Recipe language unavailable: " + locale);
        try {
            FileTime modified = Files.getLastModifiedTime(file);
            Catalog cached = cache.get(locale);
            long revision = edits.revision();
            if (cached != null && cached.modified().equals(modified) && cached.editRevision() == revision) return cached;
            if (Files.size(file) > 8_000_000) throw new IllegalStateException("Recipe catalog is too large: " + file);
            JsonNode root = json.readTree(Files.readAllBytes(file));
            JsonNode metadata = root.path("metadata");
            if (!List.of("1.1.0", "1.2.0").contains(metadata.path("schema_version").asString()) ||
                !locale.equals(metadata.path("language").asString())) {
                throw new IllegalStateException("Unsupported or mismatched recipe catalog: " + file);
            }
            JsonNode rows = root.path("recipes");
            if (!rows.isArray()) throw new IllegalStateException("Missing recipes array: " + file);
            Map<String, JsonNode> raw = new LinkedHashMap<>();
            List<Recipe> recipes = new ArrayList<>();
            Map<String, Recipe> byId = new HashMap<>();
            for (JsonNode row : rows) {
                Recipe recipe = mapper.recipe(row, locale);
                if (recipe.id().isBlank() || recipe.name().isBlank() || recipe.ingredients().isEmpty() ||
                    byId.putIfAbsent(recipe.id(), recipe) != null) {
                    throw new IllegalStateException("Invalid or duplicate recipe in " + file);
                }
                recipes.add(recipe);
                raw.put(recipe.id(), row);
            }
            if (metadata.path("recipe_count").asInt(-1) != recipes.size())
                throw new IllegalStateException("Recipe count does not match metadata: " + file);
            var changes = edits.snapshot();
            changes.deleted().forEach(raw::remove);
            for (var entry : changes.upserts().entrySet()) {
                if (!entry.getValue().containsKey(locale)) continue;
                JsonNode translated = entry.getValue().get(locale);
                if (translated == null || translated.isNull()) raw.remove(entry.getKey());
                else raw.put(entry.getKey(), translated);
            }
            recipes = new ArrayList<>();
            byId = new HashMap<>();
            for (JsonNode row : raw.values()) {
                Recipe recipe = mapper.recipe(row, locale);
                if (recipe.id().isBlank() || recipe.name().isBlank() || recipe.ingredients().isEmpty() ||
                    byId.putIfAbsent(recipe.id(), recipe) != null) {
                    throw new IllegalStateException("Invalid edited recipe in " + locale);
                }
                recipes.add(recipe);
            }
            var baseInfo = mapper.info(metadata, locale, recipes.size());
            int countries = (int) raw.values().stream().map(row -> row.path("country_code").asString())
                .filter(code -> !code.isBlank()).distinct().count();
            int regions = (int) raw.values().stream().map(row -> row.path("region_code").asString())
                .filter(code -> !code.isBlank()).distinct().count();
            CatalogInfo info = new CatalogInfo(locale, baseInfo.dataset(), recipes.size(), countries, regions,
                baseInfo.quantityNote(), baseInfo.dietNote(), baseInfo.originNote(), baseInfo.quality());
            Catalog loaded = new Catalog(modified, revision, List.copyOf(recipes), Map.copyOf(byId), Map.copyOf(raw), info);
            cache.put(locale, loaded);
            return loaded;
        } catch (IOException e) { throw new IllegalStateException("Could not read recipe catalog: " + file, e); }
    }
    public List<Recipe> findAll(String locale) { return catalog(locale).recipes(); }
    public CatalogInfo info(String locale) { return catalog(locale).info(); }
    public Optional<JsonNode> raw(String locale, String id) { return Optional.ofNullable(catalog(locale).rawById().get(id)); }
    public List<JsonNode> rawAll(String locale) { return List.copyOf(catalog(locale).rawById().values()); }
    public List<String> ids() {
        return locales().stream().flatMap(locale -> catalog(locale).rawById().keySet().stream()).distinct().sorted().toList();
    }
    public Optional<Recipe> findById(String locale, String id) {
        String normalized = RecipeLocale.normalize(locale);
        if (locales().contains(normalized)) {
            Recipe recipe = catalog(normalized).byId().get(id);
            if (recipe != null) return Optional.of(recipe);
        }
        return Optional.empty();
    }
    public boolean exists(String id) {
        return locales().stream().anyMatch(locale -> catalog(locale).byId().containsKey(id));
    }
}
