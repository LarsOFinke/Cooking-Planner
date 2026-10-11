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
    public RecipeService(RecipeRepository repository) { this.repository = repository; }
    public List<String> locales() { return repository.locales(); }
    public List<Recipe> list(String locale) { return repository.findAll(locale); }
    public CatalogInfo info(String locale) { return repository.info(locale); }
    public Recipe get(String locale, String id) {
        return repository.findById(locale, id).orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Recipe not found"));
    }
}
