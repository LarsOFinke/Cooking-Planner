package dev.cookingplanner.recipes.repositories;

import dev.cookingplanner.recipes.dtos.RecipeInput;
import dev.cookingplanner.recipes.entities.Recipe;
import dev.cookingplanner.shared.JsonFileStore;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.TreeSet;
import org.springframework.stereotype.Repository;
import tools.jackson.core.type.TypeReference;

@Repository
public class RecipeRepository {
    private final JsonFileStore store;
    public RecipeRepository(JsonFileStore store) { this.store = store; }

    private String file(String locale) { return "recipes_" + locale + ".json"; }
    private String readableFile(String locale) {
        // Existing V1 installations used recipes.json for English recipes.
        if (locale.equals("en") && !store.fileNames().contains(file("en")) && store.fileNames().contains("recipes.json")) return "recipes.json";
        return file(locale);
    }
    private List<Recipe> read(String locale) {
        return store.read(readableFile(locale), new TypeReference<List<Recipe>>() {}, List.of()).stream()
            .map(recipe -> new Recipe(recipe.id(), recipe.title(), recipe.category(), recipe.ingredients(),
                recipe.instructions(), recipe.prepMinutes(), locale)).toList();
    }
    public synchronized List<String> locales() {
        Set<String> locales = new TreeSet<>();
        for (String name : store.fileNames()) {
            if (name.matches("recipes_[a-z]{2}\\.json")) locales.add(name.substring(8, 10));
            if (name.equals("recipes.json")) locales.add("en");
        }
        if (locales.isEmpty()) locales.add("en");
        return List.copyOf(locales);
    }
    public synchronized List<Recipe> findAll(String locale) {
        return read(locale).stream().sorted(Comparator.comparing(Recipe::category, String.CASE_INSENSITIVE_ORDER)
            .thenComparing(Recipe::title, String.CASE_INSENSITIVE_ORDER)).toList();
    }
    public synchronized Optional<Recipe> findById(long id) {
        return locales().stream().flatMap(locale -> read(locale).stream()).filter(recipe -> recipe.id() == id).findFirst();
    }
    public synchronized Recipe create(String locale, RecipeInput input) { return importAll(locale, List.of(input)).getFirst(); }
    public synchronized List<Recipe> importAll(String locale, List<RecipeInput> inputs) {
        List<Recipe> recipes = new ArrayList<>(read(locale));
        long nextId = locales().stream().flatMap(language -> read(language).stream()).mapToLong(Recipe::id).max().orElse(0) + 1;
        List<Recipe> added = new ArrayList<>();
        for (RecipeInput input : inputs) {
            Recipe recipe = new Recipe(nextId++, input.title().trim(), input.category().trim(),
                List.copyOf(input.ingredients()), input.instructions().trim(), input.prepMinutes(), locale);
            recipes.add(recipe); added.add(recipe);
        }
        store.write(file(locale), recipes);
        return added;
    }
    public synchronized Recipe update(long id, RecipeInput input) {
        Recipe existing = findById(id).orElseThrow(() -> new IllegalArgumentException("Recipe not found"));
        List<Recipe> recipes = new ArrayList<>(read(existing.locale()));
        Recipe updated = new Recipe(id, input.title().trim(), input.category().trim(), List.copyOf(input.ingredients()), input.instructions().trim(), input.prepMinutes(), existing.locale());
        recipes.removeIf(recipe -> recipe.id() == id);
        recipes.add(updated); store.write(file(existing.locale()), recipes); return updated;
    }
    public synchronized void delete(long id) {
        Optional<Recipe> existing = findById(id);
        if (existing.isEmpty()) return;
        String locale = existing.get().locale();
        List<Recipe> recipes = new ArrayList<>(read(locale));
        if (recipes.removeIf(recipe -> recipe.id() == id)) store.write(file(locale), recipes);
    }
}
