package dev.cookingplanner.recipes.controllers;

import dev.cookingplanner.recipes.services.RecipeAdminService;
import dev.cookingplanner.recipes.services.RecipeAdminService.EditInput;
import java.util.List;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/admin/recipes")
public class RecipeAdminController {
    private final RecipeAdminService service;
    public RecipeAdminController(RecipeAdminService service) { this.service = service; }

    @GetMapping public List<Map<String, Object>> list() { return service.list(); }
    @GetMapping("/options")
    public Map<String, Map<String, List<Map<String, String>>>> options() { return service.options(); }
    @GetMapping("/{id}") public Map<String, Object> get(@PathVariable String id) { return service.get(id); }
    @PostMapping("/{id}") @ResponseStatus(HttpStatus.CREATED)
    public Map<String, Object> create(@PathVariable String id, @RequestBody EditInput input) {
        return service.save(id, input, true);
    }
    @PutMapping("/{id}") public Map<String, Object> update(@PathVariable String id, @RequestBody EditInput input) {
        return service.save(id, input, false);
    }
    @DeleteMapping("/{id}") @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@PathVariable String id) { service.delete(id); }

    @ExceptionHandler(ResponseStatusException.class)
    public ResponseEntity<Map<String, String>> invalidEdit(ResponseStatusException error) {
        return ResponseEntity.status(error.getStatusCode()).body(Map.of("message", error.getReason()));
    }
}
