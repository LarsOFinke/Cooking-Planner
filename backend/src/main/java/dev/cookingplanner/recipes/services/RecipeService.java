package dev.cookingplanner.recipes.services;

import dev.cookingplanner.recipes.RecipeLocale;
import dev.cookingplanner.recipes.dtos.RecipeInput;
import dev.cookingplanner.recipes.entities.Recipe;
import dev.cookingplanner.recipes.repositories.RecipeRepository;
import dev.cookingplanner.plans.repositories.MealPlanRepository;
import jakarta.validation.Valid;
import jakarta.validation.Validator;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

@Service
public class RecipeService {
    private final RecipeRepository repository;
    private final Validator validator;
    private final MealPlanRepository plans;

    public RecipeService(RecipeRepository repository, Validator validator, MealPlanRepository plans) { this.repository = repository; this.validator = validator; this.plans = plans; }
    public List<String> locales() { return repository.locales(); }
    public List<Recipe> list(String locale) { return repository.findAll(RecipeLocale.normalize(locale)); }
    public Recipe create(String locale, @Valid RecipeInput input) { return repository.create(RecipeLocale.normalize(locale), input); }
    public Recipe update(long id, @Valid RecipeInput input) {
        repository.findById(id).orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Recipe not found"));
        return repository.update(id, input);
    }
    public void delete(long id) {
        repository.findById(id).orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Recipe not found"));
        if (plans.hasRecipe(id)) throw new ResponseStatusException(HttpStatus.CONFLICT, "Remove planned meals before deleting recipe");
        repository.delete(id);
    }
    public List<Recipe> importRecipes(String locale, List<RecipeInput> inputs) {
        String language = RecipeLocale.normalize(locale);
        if (inputs == null || inputs.isEmpty() || inputs.size() > 500) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Expected 1 to 500 recipes");
        for (RecipeInput input : inputs) {
            if (input == null || !validator.validate(input).isEmpty()) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Invalid recipe in import");
        }
        return repository.importAll(language, inputs);
    }
}
