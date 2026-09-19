import importlib.util
import pathlib

# Wrap the top-level scripts/load_synthetic_data.py so tests can import via src.scripts
root = pathlib.Path(__file__).resolve().parents[2]
script_path = root / 'scripts' / 'load_synthetic_data.py'
spec = importlib.util.spec_from_file_location('ace.load_synthetic_data', str(script_path))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Expose main
main = getattr(mod, 'main')
