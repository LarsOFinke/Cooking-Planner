package dev.cookingplanner.recipes.repositories;

import dev.cookingplanner.recipes.entities.IngredientEntity;
import org.springframework.data.jpa.repository.JpaRepository;

public interface IngredientJpaRepository extends JpaRepository<IngredientEntity, String> {}
