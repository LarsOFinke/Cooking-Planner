package dev.cookingplanner.shared;

import com.zaxxer.hikari.HikariDataSource;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
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
        return source;
    }
}
