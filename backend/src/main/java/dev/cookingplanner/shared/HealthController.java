package dev.cookingplanner.shared;

import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HealthController {
    private final String instanceToken;

    public HealthController(@Value("${COOKING_PLANNER_INSTANCE_TOKEN:}") String instanceToken) {
        this.instanceToken = instanceToken;
    }

    @GetMapping("/api/health") public Map<String, String> health() {
        return Map.of("status", "ok", "instanceToken", instanceToken);
    }
}
