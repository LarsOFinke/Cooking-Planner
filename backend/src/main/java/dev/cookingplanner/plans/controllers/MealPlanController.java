package dev.cookingplanner.plans.controllers;

import dev.cookingplanner.plans.dtos.MealPlanInput;
import dev.cookingplanner.plans.entities.MealPlan;
import dev.cookingplanner.plans.services.MealPlanService;
import dev.cookingplanner.plans.services.ShoppingService;
import dev.cookingplanner.plans.entities.ShoppingItem;
import jakarta.validation.Valid;
import java.time.LocalDate;
import java.util.List;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/plans")
public class MealPlanController {
    private final MealPlanService service;
    private final ShoppingService shopping;
    public MealPlanController(MealPlanService service, ShoppingService shopping) { this.service = service; this.shopping = shopping; }
    @GetMapping public List<MealPlan> list(@RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
        @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to,
        @RequestParam(defaultValue = "en") String locale) { return service.list(from, to, locale); }
    @PutMapping public MealPlan save(@Valid @RequestBody MealPlanInput input) { return service.save(input); }
    @GetMapping("/shopping") public List<ShoppingItem> shopping(
        @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
        @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to,
        @RequestParam(defaultValue = "en") String locale) { return shopping.list(from, to, locale); }
    @DeleteMapping("/{id}") @ResponseStatus(HttpStatus.NO_CONTENT) public void delete(@PathVariable long id) { service.delete(id); }
}
