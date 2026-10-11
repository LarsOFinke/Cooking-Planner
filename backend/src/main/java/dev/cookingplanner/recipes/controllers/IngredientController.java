package dev.cookingplanner.recipes.controllers;

import dev.cookingplanner.recipes.services.IngredientService;
import dev.cookingplanner.recipes.services.IngredientService.Match;
import dev.cookingplanner.recipes.services.IngredientService.PriceInput;
import java.util.List;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/ingredients")
public class IngredientController {
    private final IngredientService service;
    public IngredientController(IngredientService service) { this.service = service; }

    @GetMapping
    public List<Match> search(@RequestParam(defaultValue = "en") String locale,
        @RequestParam(defaultValue = "") String q) { return service.search(locale, q); }

    @PostMapping @ResponseStatus(HttpStatus.CREATED)
    public Match create(@RequestBody IngredientService.NewIngredient input) { return service.create(input); }

    @GetMapping("/prices")
    public Map<String, String> prices(@RequestParam String week) { return service.prices(week); }

    @DeleteMapping("/prices")
    public void clearPrices(@RequestParam String week) { service.clearPrices(week); }

    @PutMapping("/{id}/prices")
    public void savePrice(@PathVariable String id, @RequestParam String week, @RequestParam String unit,
        @RequestBody PriceInput input) { service.savePrice(id, week, unit, input); }
}
