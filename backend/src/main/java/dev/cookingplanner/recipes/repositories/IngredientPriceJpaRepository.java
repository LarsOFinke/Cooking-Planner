package dev.cookingplanner.recipes.repositories;

import dev.cookingplanner.recipes.entities.IngredientPriceEntity;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface IngredientPriceJpaRepository extends JpaRepository<IngredientPriceEntity, Integer> {
    List<IngredientPriceEntity> findByWeekStart(String weekStart);
    Optional<IngredientPriceEntity> findByIngredientIdAndWeekStartAndUnit(
        String ingredientId, String weekStart, String unit);
    void deleteByWeekStart(String weekStart);
    boolean existsByIngredientId(String ingredientId);
}
