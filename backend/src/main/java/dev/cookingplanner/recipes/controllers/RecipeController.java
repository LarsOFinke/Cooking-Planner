package dev.cookingplanner.recipes.controllers;

import dev.cookingplanner.recipes.dtos.RecipeInput;
import dev.cookingplanner.recipes.entities.Recipe;
import dev.cookingplanner.recipes.services.RecipeService;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/recipes")
public class RecipeController {
    private final RecipeService service;
    public RecipeController(RecipeService service) { this.service = service; }
    @GetMapping("/locales") public List<String> locales() { return service.locales(); }
    @GetMapping public List<Recipe> list(@RequestParam(defaultValue = "en") String locale) { return service.list(locale); }
    @PostMapping @ResponseStatus(HttpStatus.CREATED) public Recipe create(@RequestParam(defaultValue = "en") String locale, @Valid @RequestBody RecipeInput input) { return service.create(locale, input); }
    @PutMapping("/{id}") public Recipe update(@PathVariable long id, @Valid @RequestBody RecipeInput input) { return service.update(id, input); }
    @DeleteMapping("/{id}") @ResponseStatus(HttpStatus.NO_CONTENT) public void delete(@PathVariable long id) { service.delete(id); }
    @PostMapping("/import") @ResponseStatus(HttpStatus.CREATED) public List<Recipe> importRecipes(@RequestParam(defaultValue = "en") String locale, @RequestBody List<RecipeInput> inputs) { return service.importRecipes(locale, inputs); }
}
