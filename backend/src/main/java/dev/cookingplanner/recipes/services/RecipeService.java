package dev.cookingplanner.recipes.services;

import dev.cookingplanner.recipes.entities.CatalogInfo;
import dev.cookingplanner.recipes.entities.Recipe;
import dev.cookingplanner.recipes.repositories.RecipeRepository;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

@Service
public class RecipeService {
    private final RecipeRepository repository;
    private final IngredientService ingredients;
    public RecipeService(RecipeRepository repository, IngredientService ingredients) {
        this.repository = repository; this.ingredients = ingredients;
    }
    public List<String> locales() { return repository.locales(); }
    public List<Recipe> list(String locale) { return ingredients.localizeAll(repository.findAll(locale)); }
    public CatalogInfo info(String locale) { return repository.info(locale); }
    public Recipe get(String locale, String id) {
        return ingredients.localize(repository.findById(locale, id)
            .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Recipe not found")));
    }
}
