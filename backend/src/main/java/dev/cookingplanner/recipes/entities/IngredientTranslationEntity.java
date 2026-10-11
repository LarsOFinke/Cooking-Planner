package dev.cookingplanner.recipes.entities;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;

@Entity
@Table(name = "ingredient_translation", uniqueConstraints =
    @UniqueConstraint(columnNames = {"ingredient_id", "locale"}))
public class IngredientTranslationEntity {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;
    @Column(name = "ingredient_id", nullable = false)
    private String ingredientId;
    @Column(nullable = false)
    private String locale;
    @Column(nullable = false)
    private String name;

    protected IngredientTranslationEntity() {}
    public IngredientTranslationEntity(String ingredientId, String locale, String name) {
        this.ingredientId = ingredientId; this.locale = locale; this.name = name;
    }
    public Integer getId() { return id; }
    public String getIngredientId() { return ingredientId; }
    public String getLocale() { return locale; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
}
