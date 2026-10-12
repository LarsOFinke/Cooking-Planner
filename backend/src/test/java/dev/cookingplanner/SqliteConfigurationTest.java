package dev.cookingplanner;

import static org.junit.jupiter.api.Assertions.*;

import com.zaxxer.hikari.HikariDataSource;
import dev.cookingplanner.shared.SqliteConfiguration;
import java.nio.file.Path;
import java.sql.DriverManager;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class SqliteConfigurationTest {
    @TempDir Path directory;

    @Test
    void addsPriceBasisWithoutChangingExistingWeekPrices() throws Exception {
        String url = "jdbc:sqlite:" + directory.resolve("cooking-planner.db");
        try (var connection = DriverManager.getConnection(url); var statement = connection.createStatement()) {
            statement.execute("CREATE TABLE ingredient_price (id INTEGER PRIMARY KEY, ingredient_id TEXT, " +
                "week_start TEXT, unit TEXT, amount_cents INTEGER)");
            statement.execute("INSERT INTO ingredient_price VALUES (1, 'rice', '2026-10-05', 'g', 250)");
        }
        try (var source = (HikariDataSource) new SqliteConfiguration().dataSource(directory.toString());
             var connection = source.getConnection(); var statement = connection.createStatement();
             var prices = statement.executeQuery("SELECT amount_cents, basis_quantity FROM ingredient_price")) {
            assertTrue(prices.next());
            assertEquals(250, prices.getInt("amount_cents"));
            assertNull(prices.getObject("basis_quantity"));
        }
    }
}
