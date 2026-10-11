package dev.cookingplanner.recipes.controllers;

import dev.cookingplanner.recipes.services.IngredientService;
import dev.cookingplanner.recipes.services.IngredientService.CatalogEntry;
import dev.cookingplanner.recipes.services.IngredientService.CatalogInput;
import java.util.List;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/admin/ingredients")
public class IngredientAdminController {
    private final IngredientService service;

    public IngredientAdminController(IngredientService service) { this.service = service; }

    @GetMapping
    public List<CatalogEntry> list(@RequestParam(defaultValue = "") String q) {
        return service.catalog(q);
    }

    @GetMapping("/{id}")
    public CatalogEntry get(@PathVariable String id) { return service.catalogEntry(id); }

    @PutMapping("/{id}")
    public CatalogEntry save(@PathVariable String id, @RequestBody CatalogInput input) {
        return service.saveCatalogEntry(id, input);
    }

    @DeleteMapping("/{id}")
    public void delete(@PathVariable String id) { service.deleteCatalogEntry(id); }
}
