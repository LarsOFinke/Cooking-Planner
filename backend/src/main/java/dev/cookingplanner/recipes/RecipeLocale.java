package dev.cookingplanner.recipes;

import java.util.Locale;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

public final class RecipeLocale {
    private RecipeLocale() {}
    public static String normalize(String value) {
        String locale = value == null ? "" : value.toLowerCase(Locale.ROOT);
        if (!locale.matches("[a-z]{2}")) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Language must be a two-letter code");
        return locale;
    }
}
