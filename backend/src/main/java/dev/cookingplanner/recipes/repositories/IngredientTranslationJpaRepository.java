package dev.cookingplanner.recipes.repositories;

import dev.cookingplanner.recipes.entities.IngredientTranslationEntity;
import java.util.List;
import java.util.Optional;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface IngredientTranslationJpaRepository extends JpaRepository<IngredientTranslationEntity, Integer> {
    Optional<IngredientTranslationEntity> findByIngredientIdAndLocale(String ingredientId, String locale);
    List<IngredientTranslationEntity> findByLocaleAndNameContainingIgnoreCaseOrderByNameAsc(
        String locale, String name, Pageable page);
    List<IngredientTranslationEntity> findByIngredientIdIn(List<String> ingredientIds);
    List<IngredientTranslationEntity> findByIngredientId(String ingredientId);
    List<IngredientTranslationEntity> findByLocale(String locale);
}
