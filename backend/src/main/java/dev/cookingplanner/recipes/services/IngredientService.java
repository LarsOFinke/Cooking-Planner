package dev.cookingplanner.recipes.services;

import dev.cookingplanner.recipes.entities.Ingredient;
import dev.cookingplanner.recipes.entities.IngredientEntity;
import dev.cookingplanner.recipes.entities.IngredientPriceEntity;
import dev.cookingplanner.recipes.entities.IngredientTranslationEntity;
import dev.cookingplanner.recipes.entities.Recipe;
import dev.cookingplanner.recipes.repositories.IngredientJpaRepository;
import dev.cookingplanner.recipes.repositories.IngredientPriceJpaRepository;
import dev.cookingplanner.recipes.repositories.IngredientTranslationJpaRepository;
import dev.cookingplanner.recipes.repositories.RecipeRepository;
import jakarta.transaction.Transactional;
import java.math.BigDecimal;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.time.DateTimeException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ObjectNode;

@Service
public class IngredientService implements ApplicationRunner {
    private static final Logger log = LoggerFactory.getLogger(IngredientService.class);
    public record Match(String id, String name, Map<String, String> translations) {}
    public record PriceInput(String price) {}
    public record ReferencePriceInput(String price, Integer basisQuantity) {}
    public record ReferencePrice(String price, int basisQuantity) {}
    public record NewIngredient(String id, String locale, String name) {}
    public record CatalogInput(Map<String, String> translations) {}
    public record CatalogEntry(String id, Map<String, String> translations) {}

    private final IngredientJpaRepository ingredients;
    private final IngredientTranslationJpaRepository translations;
    private final IngredientPriceJpaRepository prices;
    private final RecipeRepository recipes;
    private final JdbcTemplate jdbc;
    private final ObjectMapper json;
    private final Path dataDirectory;

    public IngredientService(IngredientJpaRepository ingredients,
        IngredientTranslationJpaRepository translations, IngredientPriceJpaRepository prices,
        RecipeRepository recipes, JdbcTemplate jdbc, ObjectMapper json,
        @Value("${cooking-planner.data-dir}") String dataDirectory) {
        this.ingredients = ingredients; this.translations = translations; this.prices = prices;
        this.recipes = recipes; this.jdbc = jdbc; this.json = json;
        this.dataDirectory = Path.of(dataDirectory).toAbsolutePath();
    }

    @Override
    @Transactional
    public void run(ApplicationArguments arguments) throws Exception {
        // Read the catalog and edit overlay before touching the new database.
        Map<String, Map<String, String>> names = new LinkedHashMap<>();
        for (String locale : recipes.locales()) {
            for (JsonNode recipe : recipes.rawAll(locale)) {
                for (JsonNode row : recipe.path("ingredients")) {
                    String id = row.path("ingredient_id").asString();
                    String name = row.path("name").asString();
                    if (!id.isBlank() && !name.isBlank())
                        names.computeIfAbsent(id, ignored -> new LinkedHashMap<>()).putIfAbsent(locale, name);
                }
            }
        }
        Map<String, IngredientEntity> existing = new HashMap<>();
        ingredients.findAll().forEach(row -> existing.put(row.getId(), row));
        Map<String, IngredientTranslationEntity> existingNames = new HashMap<>();
        translations.findAll().forEach(row -> existingNames.put(row.getIngredientId() + ':' + row.getLocale(), row));
        for (var entry : names.entrySet()) {
            if (!existing.containsKey(entry.getKey())) ingredients.save(new IngredientEntity(entry.getKey()));
            for (var name : entry.getValue().entrySet()) {
                String key = entry.getKey() + ':' + name.getKey();
                if (!existingNames.containsKey(key))
                    translations.save(new IngredientTranslationEntity(entry.getKey(), name.getKey(), name.getValue()));
            }
        }
        try { importLegacyPrices(); }
        catch (IOException | DateTimeException | IllegalArgumentException | IllegalStateException error) {
            log.warn("Could not import legacy shopping prices; shopping.json was left unchanged", error);
        }
    }

    private void importLegacyPrices() throws IOException {
        Integer migrated = jdbc.queryForObject(
            "SELECT count(*) FROM migration_marker WHERE name = 'shopping-prices-v1'", Integer.class);
        if (migrated != null && migrated != 0) return;
        Path file = dataDirectory.resolve("shopping.json");
        if (Files.isRegularFile(file)) {
            JsonNode root = json.readTree(Files.readAllBytes(file));
            if (root.path("version").asInt(-1) != 1 || !root.path("weeks").isObject())
                throw new IllegalStateException("Unsupported shopping draft; original was not changed");
            List<IngredientPriceEntity> imported = new ArrayList<>();
            for (var weeks = root.path("weeks").properties().iterator(); weeks.hasNext();) {
                var week = weeks.next();
                LocalDate.parse(week.getKey());
                JsonNode oldPrices = week.getValue().path("prices");
                if (!oldPrices.isObject() && !oldPrices.isMissingNode())
                    throw new IllegalStateException("Invalid shopping prices; original was not changed");
                for (var rows = oldPrices.properties().iterator(); rows.hasNext();) {
                    var row = rows.next();
                    int split = row.getKey().lastIndexOf(':');
                    if (split < 1 || !row.getValue().isString())
                        throw new IllegalStateException("Invalid shopping price; original was not changed");
                    String id = row.getKey().substring(0, split);
                    String unit = row.getKey().substring(split + 1);
                    BigDecimal amount = validPrice(row.getValue().asString());
                    imported.add(new IngredientPriceEntity(id, week.getKey(), unit, amount));
                }
            }
            for (var price : imported) {
                if (!ingredients.existsById(price.getIngredientId()))
                    ingredients.save(new IngredientEntity(price.getIngredientId()));
                if (prices.findByIngredientIdAndWeekStartAndUnit(
                    price.getIngredientId(), price.getWeekStart(), price.getUnit()).isEmpty())
                    prices.save(price);
            }
            if (!imported.isEmpty())
                jdbc.update("INSERT INTO migration_marker(name) VALUES ('shopping-prices-v1')");
        }
    }

    @Transactional
    public void register(Map<String, JsonNode> translatedRecipes) {
        for (var translation : translatedRecipes.entrySet()) {
            JsonNode recipe = translation.getValue();
            if (recipe == null || recipe.isNull()) continue;
            for (JsonNode row : recipe.path("ingredients")) {
                String id = row.path("ingredient_id").asString();
                String name = row.path("name").asString();
                if (!ingredients.existsById(id)) ingredients.save(new IngredientEntity(id));
                var existing = translations.findByIngredientIdAndLocale(id, translation.getKey());
                if (existing.isPresent()) {
                    existing.get().setName(name);
                    translations.save(existing.get());
                } else translations.save(new IngredientTranslationEntity(id, translation.getKey(), name));
            }
        }
    }

    public List<Match> search(String locale, String query) {
        if (query == null || query.isBlank()) return List.of();
        String normalized = locale == null ? "en" : locale.toLowerCase();
        List<IngredientTranslationEntity> found = translations
            .findByLocaleAndNameContainingIgnoreCaseOrderByNameAsc(normalized, query.trim(), PageRequest.of(0, 40));
        List<String> ids = found.stream().map(IngredientTranslationEntity::getIngredientId).toList();
        Map<String, Map<String, String>> names = new HashMap<>();
        if (!ids.isEmpty()) for (var row : translations.findByIngredientIdIn(ids))
            names.computeIfAbsent(row.getIngredientId(), ignored -> new LinkedHashMap<>())
                .put(row.getLocale(), row.getName());
        List<Match> result = new ArrayList<>();
        for (var row : found) result.add(new Match(row.getIngredientId(), row.getName(),
            Map.copyOf(names.get(row.getIngredientId()))));
        return result;
    }

    @Transactional
    public Match create(NewIngredient input) {
        if (input == null || input.id() == null ||
            !input.id().matches("[a-z0-9]+(?:-[a-z0-9]+)*") || input.id().length() > 120 ||
            input.locale() == null || !recipes.locales().contains(input.locale()) ||
            input.name() == null || input.name().isBlank() || input.name().length() > 180)
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Valid ingredient ID, language and name are required");
        if (!ingredients.existsById(input.id())) ingredients.save(new IngredientEntity(input.id()));
        var name = translations.findByIngredientIdAndLocale(input.id(), input.locale());
        if (name.isPresent() && !name.get().getName().equals(input.name().trim()))
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Ingredient ID already has a different name");
        if (name.isEmpty())
            translations.save(new IngredientTranslationEntity(input.id(), input.locale(), input.name().trim()));
        return new Match(input.id(), input.name().trim(), Map.of(input.locale(), input.name().trim()));
    }

    public List<CatalogEntry> catalog(String query) {
        String needle = query == null ? "" : query.trim().toLowerCase();
        Map<String, Map<String, String>> names = new LinkedHashMap<>();
        for (var ingredient : ingredients.findAll())
            names.put(ingredient.getId(), new LinkedHashMap<>());
        for (var translation : translations.findAll())
            names.computeIfAbsent(translation.getIngredientId(), ignored -> new LinkedHashMap<>())
                .put(translation.getLocale(), translation.getName());
        return names.entrySet().stream()
            .filter(entry -> needle.isEmpty() || entry.getKey().toLowerCase().contains(needle) ||
                entry.getValue().values().stream().anyMatch(name -> name.toLowerCase().contains(needle)))
            .sorted((left, right) -> left.getKey().compareTo(right.getKey()))
            .map(entry -> new CatalogEntry(entry.getKey(), Map.copyOf(entry.getValue()))).toList();
    }

    public CatalogEntry catalogEntry(String id) {
        if (!ingredients.existsById(id))
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Ingredient not found");
        Map<String, String> names = new LinkedHashMap<>();
        for (var translation : translations.findByIngredientId(id))
            names.put(translation.getLocale(), translation.getName());
        return new CatalogEntry(id, names);
    }

    @Transactional
    public CatalogEntry saveCatalogEntry(String id, CatalogInput input) {
        if (id == null || !id.matches("[a-z0-9]+(?:-[a-z0-9]+)*") || id.length() > 120 ||
            input == null || input.translations() == null ||
            !recipes.locales().containsAll(input.translations().keySet()) ||
            input.translations().values().stream().noneMatch(name -> name != null && !name.isBlank()))
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Ingredient ID and a translated name are required");
        Map<String, String> requested = new LinkedHashMap<>();
        for (String locale : recipes.locales()) {
            String name = input.translations().getOrDefault(locale, "");
            if (name == null || name.trim().length() > 180)
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Invalid ingredient name for " + locale);
            requested.put(locale, name.trim());
        }
        for (String locale : recipes.locales())
            if (requested.get(locale).isEmpty() && usedInRecipes(id, locale))
                throw new ResponseStatusException(HttpStatus.CONFLICT,
                    "Translation is used by recipes in " + locale);
        if (!ingredients.existsById(id)) ingredients.save(new IngredientEntity(id));
        for (var existing : translations.findByIngredientId(id)) {
            String name = requested.get(existing.getLocale());
            if (name == null || name.isEmpty()) translations.delete(existing);
            else {
                existing.setName(name);
                translations.save(existing);
            }
            requested.remove(existing.getLocale());
        }
        requested.forEach((locale, name) -> {
            if (!name.isEmpty()) translations.save(new IngredientTranslationEntity(id, locale, name));
        });
        return catalogEntry(id);
    }

    @Transactional
    public void deleteCatalogEntry(String id) {
        if (!ingredients.existsById(id))
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Ingredient not found");
        if (recipes.locales().stream().anyMatch(locale -> usedInRecipes(id, locale)) ||
            prices.existsByIngredientId(id) || usedInShoppingDraft(id))
            throw new ResponseStatusException(HttpStatus.CONFLICT,
                "Ingredient is used by a recipe, shopping item, or saved price");
        translations.deleteAll(translations.findByIngredientId(id));
        ingredients.deleteById(id);
    }

    private boolean usedInRecipes(String id, String locale) {
        for (JsonNode recipe : recipes.rawAll(locale))
            for (JsonNode row : recipe.path("ingredients"))
                if (id.equals(row.path("ingredient_id").asString())) return true;
        return false;
    }

    private boolean usedInShoppingDraft(String id) {
        Path file = dataDirectory.resolve("shopping.json");
        if (!Files.isRegularFile(file)) return false;
        try {
            JsonNode root = json.readTree(Files.readAllBytes(file));
            if (root.path("version").asInt(-1) != 1 || !root.path("weeks").isObject())
                throw new IllegalStateException("Unsupported shopping draft");
            for (var weeks = root.path("weeks").properties().iterator(); weeks.hasNext();) {
                JsonNode week = weeks.next().getValue();
                if (!week.isObject() || !week.path("custom").isArray())
                    throw new IllegalStateException("Unsupported shopping draft");
                for (JsonNode item : week.path("custom"))
                    if (id.equals(item.path("ingredientId").asString())) return true;
            }
            return false;
        } catch (IOException | RuntimeException error) {
            throw new ResponseStatusException(HttpStatus.CONFLICT,
                "Shopping draft cannot be checked; ingredient was not deleted", error);
        }
    }

    public Recipe localize(Recipe recipe) {
        return localize(recipe, translationMap(recipe.locale()));
    }

    public JsonNode canonicalize(JsonNode raw, String locale) {
        ObjectNode copy = (ObjectNode) raw.deepCopy();
        for (JsonNode ingredient : copy.path("ingredients")) {
            String id = ingredient.path("ingredient_id").asString();
            translations.findByIngredientIdAndLocale(id, locale)
                .ifPresent(name -> ((ObjectNode) ingredient).put("name", name.getName()));
        }
        return copy;
    }

    public List<Recipe> localizeAll(List<Recipe> recipes) {
        if (recipes.isEmpty()) return recipes;
        Map<String, String> names = translationMap(recipes.getFirst().locale());
        return recipes.stream().map(recipe -> localize(recipe, names)).toList();
    }

    private Map<String, String> translationMap(String locale) {
        Map<String, String> names = new HashMap<>();
        translations.findByLocale(locale).forEach(row -> names.put(row.getIngredientId(), row.getName()));
        return names;
    }

    private Recipe localize(Recipe recipe, Map<String, String> names) {
        List<Ingredient> localized = recipe.ingredients().stream().map(ingredient ->
            new Ingredient(names.getOrDefault(ingredient.ingredientId(), ingredient.name()),
                ingredient.ingredientId(), ingredient.amount(), ingredient.unit())).toList();
        return new Recipe(recipe.id(), recipe.name(), recipe.country(), recipe.countryCode(), recipe.region(),
            recipe.continent(), recipe.category(), recipe.categoryLabel(), recipe.difficulty(),
            recipe.difficultyLabel(), recipe.effort(), recipe.effortLabel(), recipe.dietType(),
            recipe.dietTypeLabel(), recipe.suitableFor(), recipe.suitableForLabels(), localized,
            recipe.prepMinutes(), recipe.cookMinutes(), recipe.totalMinutes(), recipe.dataSourceLabel(),
            recipe.locale(), recipe.images(), recipe.instructions());
    }

    public Map<String, String> prices(String week) {
        LocalDate.parse(week);
        Map<String, String> result = new LinkedHashMap<>();
        for (var row : prices.findByWeekStart(week))
            result.put(row.getIngredientId() + ':' + row.getUnit(), row.getAmount().toPlainString());
        return result;
    }

    public Map<String, ReferencePrice> referencePrices() {
        Map<String, ReferencePrice> result = new LinkedHashMap<>();
        for (var row : prices.findByWeekStart("*"))
            result.put(row.getIngredientId() + ':' + row.getUnit(),
                new ReferencePrice(row.getAmount().toPlainString(), row.getBasisQuantity()));
        return result;
    }

    @Transactional
    public void saveReferencePrice(String ingredientId, String unit, ReferencePriceInput input) {
        if (ingredientId == null || ingredientId.isBlank() || unit == null || unit.isBlank() || unit.length() > 24)
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Ingredient and unit are required");
        var existing = prices.findByIngredientIdAndWeekStartAndUnit(ingredientId, "*", unit);
        if (input == null || input.price() == null || input.price().isBlank()) {
            existing.ifPresent(prices::delete);
            return;
        }
        if (input.basisQuantity() == null || input.basisQuantity() <= 0 || input.basisQuantity() > 1_000_000)
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Price basis must be a positive quantity");
        BigDecimal amount;
        try { amount = validPrice(input.price()); }
        catch (IllegalArgumentException error) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, error.getMessage());
        }
        if (!ingredients.existsById(ingredientId)) ingredients.save(new IngredientEntity(ingredientId));
        if (existing.isPresent()) {
            existing.get().setAmount(amount);
            existing.get().setBasisQuantity(input.basisQuantity());
            prices.save(existing.get());
        } else prices.save(new IngredientPriceEntity(
            ingredientId, "*", unit, amount, input.basisQuantity()));
    }

    @Transactional
    public void savePrice(String ingredientId, String week, String unit, PriceInput input) {
        LocalDate.parse(week);
        if (ingredientId == null || ingredientId.isBlank() || unit == null || unit.isBlank() || unit.length() > 24)
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Ingredient and unit are required");
        var existing = prices.findByIngredientIdAndWeekStartAndUnit(ingredientId, week, unit);
        if (input == null || input.price() == null || input.price().isBlank()) {
            existing.ifPresent(prices::delete);
            return;
        }
        BigDecimal amount;
        try { amount = validPrice(input.price()); }
        catch (IllegalArgumentException error) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, error.getMessage());
        }
        if (!ingredients.existsById(ingredientId)) ingredients.save(new IngredientEntity(ingredientId));
        if (existing.isPresent()) {
            existing.get().setAmount(amount);
            prices.save(existing.get());
        } else prices.save(new IngredientPriceEntity(ingredientId, week, unit, amount));
    }

    @Transactional
    public void clearPrices(String week) {
        LocalDate.parse(week);
        prices.deleteByWeekStart(week);
    }

    private static BigDecimal validPrice(String raw) {
        try {
            BigDecimal value = new BigDecimal(raw.trim().replace(',', '.'));
            if (value.signum() < 0 || value.compareTo(new BigDecimal("1000000")) > 0 || value.scale() > 2)
                throw new NumberFormatException();
            return value.setScale(2);
        } catch (NumberFormatException error) {
            throw new IllegalArgumentException("Price must be a non-negative euro amount with at most two decimals", error);
        }
    }
}
