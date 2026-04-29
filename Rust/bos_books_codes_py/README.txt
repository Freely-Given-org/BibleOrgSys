# To activate VENV
source .env/bin/activate

# To benchmark / compare
maturin develop --release && python -O benchmark.py

# To deactivate VENV
deactivate
