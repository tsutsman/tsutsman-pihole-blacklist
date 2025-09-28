import importlib


def test_scripts_package_exposes_modules():
    scripts = importlib.import_module("scripts")
    available = dir(scripts)
    for name in ["check_lists", "generate_lists", "update_domains", "utils"]:
        assert name in available
        module = getattr(scripts, name)
        assert module.__name__.endswith(name)
