package dev.cookingplanner.recipes.entities;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.math.BigDecimal;

@Entity
@Table(name = "ingredient_price", uniqueConstraints =
    @UniqueConstraint(columnNames = {"ingredient_id", "week_start", "unit"}))
public class IngredientPriceEntity {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;
    @Column(name = "ingredient_id", nullable = false)
    private String ingredientId;
    @Column(name = "week_start", nullable = false)
    private String weekStart;
    @Column(nullable = false)
    private String unit;
    @Column(name = "amount_cents", nullable = false)
    private Integer amountCents;
    @Column(name = "basis_quantity")
    private Integer basisQuantity;

    protected IngredientPriceEntity() {}
    public IngredientPriceEntity(String ingredientId, String weekStart, String unit, BigDecimal amount) {
        this.ingredientId = ingredientId; this.weekStart = weekStart;
        this.unit = unit; setAmount(amount);
    }
    public IngredientPriceEntity(String ingredientId, String weekStart, String unit,
        BigDecimal amount, int basisQuantity) {
        this(ingredientId, weekStart, unit, amount);
        this.basisQuantity = basisQuantity;
    }
    public Integer getId() { return id; }
    public String getIngredientId() { return ingredientId; }
    public String getWeekStart() { return weekStart; }
    public String getUnit() { return unit; }
    public BigDecimal getAmount() { return BigDecimal.valueOf(amountCents, 2); }
    public Integer getBasisQuantity() { return basisQuantity; }
    public void setAmount(BigDecimal amount) { this.amountCents = amount.movePointRight(2).intValueExact(); }
    public void setBasisQuantity(Integer basisQuantity) { this.basisQuantity = basisQuantity; }
}
