package dev.cookingplanner.recipes.repositories;

import dev.cookingplanner.shared.JsonFileStore;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;
import org.springframework.stereotype.Repository;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.JsonNode;

@Repository
public class RecipeEditRepository {
    public record Edits(int version, Map<String, Map<String, JsonNode>> upserts, Set<String> deleted) {}

    private static final String FILE = "recipe-edits.json";
    private final JsonFileStore store;
    private long revision;

    public RecipeEditRepository(JsonFileStore store) { this.store = store; }

    public synchronized Edits snapshot() {
        Edits edits = store.read(FILE, new TypeReference<Edits>() {},
            new Edits(1, Map.of(), Set.of()));
        if (edits == null || edits.version() != 1 || edits.upserts() == null || edits.deleted() == null) {
            throw new IllegalStateException("Unsupported recipe edits file; original was not changed");
        }
        return edits;
    }

    public synchronized long revision() { return revision; }

    public synchronized void upsert(String id, Map<String, JsonNode> translations) {
        Edits old = snapshot();
        Map<String, Map<String, JsonNode>> rows = new LinkedHashMap<>(old.upserts());
        rows.put(id, new LinkedHashMap<>(translations));
        Set<String> deleted = new LinkedHashSet<>(old.deleted());
        deleted.remove(id);
        store.write(FILE, new Edits(1, rows, deleted));
        revision++;
    }

    public synchronized void delete(String id) {
        Edits old = snapshot();
        Map<String, Map<String, JsonNode>> rows = new LinkedHashMap<>(old.upserts());
        rows.remove(id);
        Set<String> deleted = new LinkedHashSet<>(old.deleted());
        deleted.add(id);
        store.write(FILE, new Edits(1, rows, deleted));
        revision++;
    }
}
