package dev.cookingplanner.shared;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.ObjectMapper;

@Component
public class JsonFileStore {
    private final Path directory;
    private final ObjectMapper json;

    public JsonFileStore(@Value("${cooking-planner.data-dir}") String directory, ObjectMapper json) {
        this.directory = Path.of(directory).toAbsolutePath();
        this.json = json;
    }

    public <T> T read(String name, TypeReference<T> type, T empty) {
        Path file = directory.resolve(name);
        if (!Files.exists(file)) return empty;
        try { return json.readValue(Files.readAllBytes(file), type); }
        catch (IOException e) { throw new IllegalStateException("Could not read " + name, e); }
    }

    public void write(String name, Object value) {
        try {
            Files.createDirectories(directory);
            Path temp = Files.createTempFile(directory, name, ".tmp");
            try {
                Files.write(temp, json.writeValueAsBytes(value));
                Files.move(temp, directory.resolve(name), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
            } finally { Files.deleteIfExists(temp); }
        } catch (IOException e) { throw new IllegalStateException("Could not save " + name, e); }
    }
}
