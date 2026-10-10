package dev.cookingplanner.plans.controllers;

import dev.cookingplanner.plans.dtos.MealPlanInput;
import dev.cookingplanner.plans.entities.MealPlan;
import dev.cookingplanner.plans.services.MealPlanService;
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
    public MealPlanController(MealPlanService service) { this.service = service; }
    @GetMapping public List<MealPlan> list(@RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
        @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to) { return service.list(from, to); }
    @PutMapping public MealPlan save(@Valid @RequestBody MealPlanInput input) { return service.save(input); }
    @DeleteMapping("/{id}") @ResponseStatus(HttpStatus.NO_CONTENT) public void delete(@PathVariable long id) { service.delete(id); }
}
