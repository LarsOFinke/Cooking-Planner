package dev.cookingplanner.recipes.controllers;

import dev.cookingplanner.recipes.entities.CatalogInfo;
import dev.cookingplanner.recipes.entities.Recipe;
import dev.cookingplanner.recipes.services.RecipeService;
import java.util.List;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/recipes")
public class RecipeController {
    private final RecipeService service;
    public RecipeController(RecipeService service) { this.service = service; }
    @GetMapping("/locales") public List<String> locales() { return service.locales(); }
    @GetMapping("/info") public CatalogInfo info(@RequestParam(defaultValue = "en") String locale) { return service.info(locale); }
    @GetMapping public List<Recipe> list(@RequestParam(defaultValue = "en") String locale) { return service.list(locale); }
    @GetMapping("/{id}") public Recipe get(@PathVariable String id, @RequestParam(defaultValue = "en") String locale) { return service.get(locale, id); }
}
