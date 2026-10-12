package dev.cookingplanner.plans.repositories;

import dev.cookingplanner.plans.dtos.MealPlanInput;
import dev.cookingplanner.plans.entities.MealPlan;
import dev.cookingplanner.shared.JsonFileStore;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.concurrent.ThreadLocalRandom;
import org.springframework.stereotype.Repository;
import tools.jackson.core.type.TypeReference;

@Repository
public class MealPlanRepository {
    private static final String FILE = "plans.json";
    private final JsonFileStore store;
    public MealPlanRepository(JsonFileStore store) { this.store = store; }
    private List<MealPlan> read() {
        return store.read(FILE, new TypeReference<List<MealPlan>>() {}, List.of()).stream()
            .map(plan -> new MealPlan(plan.id(), plan.date(), plan.mealType(), plan.recipeId(),
                plan.servings() < 1 ? 1 : plan.servings(), plan.recipeTitle())).toList();
    }
    public synchronized List<MealPlan> findBetween(LocalDate from, LocalDate to) {
        return read().stream().filter(p -> !p.date().isBefore(from) && !p.date().isAfter(to))
            .sorted(Comparator.comparing(MealPlan::date).thenComparing(MealPlan::mealType)).toList();
    }
    public synchronized MealPlan save(MealPlanInput input) {
        List<MealPlan> plans = new ArrayList<>(read());
        MealPlan existing = plans.stream().filter(p -> p.date().equals(input.date()) && p.mealType() == input.mealType()).findFirst().orElse(null);
        long id = existing == null ? newId(plans) : existing.id();
        plans.removeIf(p -> p.date().equals(input.date()) && p.mealType() == input.mealType());
        MealPlan plan = new MealPlan(id, input.date(), input.mealType(), input.recipeId(), input.servings(), "");
        plans.add(plan); store.write(FILE, plans); return plan;
    }
    public synchronized int delete(long id) {
        List<MealPlan> plans = new ArrayList<>(read());
        if (!plans.removeIf(p -> p.id() == id)) return 0;
        store.write(FILE, plans); return 1;
    }
    private static long newId(List<MealPlan> plans) {
        while (true) {
            long candidate = ThreadLocalRandom.current().nextLong(1, Long.MAX_VALUE);
            if (plans.stream().noneMatch(plan -> plan.id() == candidate)) return candidate;
        }
    }
}
