package dev.cookingplanner.shared;

import com.zaxxer.hikari.HikariDataSource;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.SQLException;
import javax.sql.DataSource;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class SqliteConfiguration {
    @Bean
    public DataSource dataSource(@Value("${cooking-planner.data-dir}") String directory) throws IOException {
        Path path = Path.of(directory).toAbsolutePath();
        Files.createDirectories(path);
        HikariDataSource source = new HikariDataSource();
        source.setJdbcUrl("jdbc:sqlite:" + path.resolve("cooking-planner.db"));
        source.setDriverClassName("org.sqlite.JDBC");
        source.setMaximumPoolSize(1);
        source.setConnectionInitSql("PRAGMA foreign_keys=ON");
        try (var connection = source.getConnection();
             var statement = connection.createStatement()) {
            boolean tableExists = false;
            boolean hasBasis = false;
            try (var columns = statement.executeQuery("PRAGMA table_info(ingredient_price)")) {
                while (columns.next()) {
                    tableExists = true;
                    if ("basis_quantity".equals(columns.getString("name"))) hasBasis = true;
                }
            }
            if (tableExists && !hasBasis)
                statement.execute("ALTER TABLE ingredient_price ADD COLUMN basis_quantity INTEGER");
        } catch (SQLException error) {
            source.close();
            throw new IOException("Could not upgrade saved ingredient prices", error);
        }
        return source;
    }
}
