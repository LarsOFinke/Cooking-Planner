package dev.cookingplanner.recipes.entities;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "ingredient")
public class IngredientEntity {
    @Id
    private String id;

    protected IngredientEntity() {}
    public IngredientEntity(String id) { this.id = id; }
    public String getId() { return id; }
}
