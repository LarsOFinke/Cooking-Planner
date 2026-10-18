import sys

from cooking_planner.launcher import main


def verify_package():
    """Exercise bundled Python modules and data without opening a window."""
    import os
    import tempfile
    from importlib import import_module
    from pathlib import Path

    os.environ['KIVY_NO_ARGS'] = '1'
    import kivy
    import sqlalchemy
    from cooking_planner.paths import catalog_directory
    from cooking_planner.recipes.images import image_file
    from cooking_planner_backend.core.LocalPlanner import LocalPlanner
    from kivy.core.image import ImageLoader
    from kivy.core.text import LabelBase

    if not kivy.__version__ or not sqlalchemy.__version__ or LabelBase is None:
        raise RuntimeError('Kivy or SQLAlchemy is unavailable')
    if sys.platform == 'win32':
        import_module('win32timezone')
    catalogs = catalog_directory()
    if sys.platform == 'win32':
        from kivy.uix.filechooser import FileSystemLocal

        FileSystemLocal().is_hidden(str(catalogs / 'recipes_en.json'))
    if not (catalogs / 'recipe_images' / 'IMAGE_ATTRIBUTIONS.csv').is_file():
        raise RuntimeError('Bundled image attributions are missing')
    with tempfile.TemporaryDirectory(prefix='cooking-planner-package-') as directory:
        planner = LocalPlanner(Path(directory), catalogs)
        try:
            for locale in ('de', 'en'):
                if planner.catalog_info(locale)['recipeCount'] != 586:
                    raise RuntimeError(f'Bundled {locale} catalog is incomplete')
            first = planner.recipe_store.raw_all('en')[0]
            photo = image_file(first['id'], first['images'][0])
            if photo is None:
                raise RuntimeError('Bundled recipe image is missing')
            ImageLoader.load(str(photo))
        finally:
            planner.close()

if __name__ == "__main__":
    if sys.argv[1:] == ['--verify-package']:
        verify_package()
    else:
        main()
