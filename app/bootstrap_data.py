"""
Bootstrap utility to verify and generate required data artefacts for Bed Allocation app.
Ensures that running `python app/run.py` works out-of-the-box even in a fresh clone.
"""

import os
import sys
import shutil
import pickle
import subprocess
import numpy as np
import pandas as pd


def get_paths(root=None):
    if root is None:
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return {
        "ROOT": root,
        "DATA_DIR": os.path.join(root, "data"),
        "APP_DATA_DIR": os.path.join(root, "app", "app", "data"),
        "FAKE_DATA_DIR": os.path.join(root, "fake_data_generation"),
        "INTEGRATION_DIR": os.path.join(root, "tests", "integration"),
    }


def check_artefacts_exist(paths=None):
    if paths is None:
        paths = get_paths()
    data_dir = paths["DATA_DIR"]
    app_data_dir = paths["APP_DATA_DIR"]

    required_files = [
        os.path.join(data_dir, "patient_df.csv"),
        os.path.join(data_dir, "historic_admissions.csv"),
        os.path.join(data_dir, "hourly_elective_prob.json"),
        os.path.join(data_dir, "specialty_info.json"),
        os.path.join(data_dir, "forecast_results.pkl"),
        os.path.join(data_dir, "hospital.pkl"),
        os.path.join(app_data_dir, "forecast_percentiles.pkl"),
        os.path.join(app_data_dir, "forecast_aggregated_percentiles.pkl"),
        os.path.join(app_data_dir, "forecast_split_random.pkl"),
        os.path.join(app_data_dir, "wards.csv"),
    ]

    return all(os.path.exists(f) for f in required_files)


def generate_synthetic_forecast_artefacts(paths):
    from forecasting.utils import (
        START_FORECAST,
        HISTORIC_HOURS,
        FORECAST_HOURS,
        HOURS_IN_WEEK,
    )

    data_dir = paths["DATA_DIR"]
    app_data_dir = paths["APP_DATA_DIR"]

    n_hours = HISTORIC_HOURS + HOURS_IN_WEEK + FORECAST_HOURS
    start = START_FORECAST - pd.Timedelta(hours=HISTORIC_HOURS)
    times = pd.date_range(start, periods=n_hours, freq="h")

    rng = np.random.RandomState(42)
    n_samples = 100
    hour_pattern = np.array([
        0.5, 0.3, 0.2, 0.2, 0.3, 0.5, 1.0, 1.8, 2.5, 3.0, 3.2, 3.0,
        2.8, 2.5, 2.2, 2.0, 1.8, 1.5, 1.2, 1.0, 0.8, 0.7, 0.6, 0.5,
    ])
    base_rates = np.tile(hour_pattern, n_hours // 24 + 1)[:n_hours]
    posterior = np.array([
        rng.poisson(lam=base_rates) for _ in range(n_samples)
    ]).astype(float)

    forecast_results = {
        "time": times,
        "posterior": posterior,
    }
    os.makedirs(data_dir, exist_ok=True)
    with open(os.path.join(data_dir, "forecast_results.pkl"), "wb") as f:
        pickle.dump(forecast_results, f)

    os.makedirs(app_data_dir, exist_ok=True)

    lower = np.percentile(posterior, 5, axis=0)
    upper = np.percentile(posterior, 95, axis=0)
    median_vals = np.percentile(posterior, 50, axis=0)

    percentiles_array = np.array([lower, median_vals, upper])
    percentiles = {
        "time": times,
        "percentiles": percentiles_array,
    }
    with open(os.path.join(app_data_dir, "forecast_percentiles.pkl"), "wb") as f:
        pickle.dump(percentiles, f)

    aggregated = {
        "time": times,
        "lower": lower,
        "upper": upper,
        "median": median_vals,
    }
    with open(os.path.join(app_data_dir, "forecast_aggregated_percentiles.pkl"), "wb") as f:
        pickle.dump(aggregated, f)

    patient_csv = os.path.join(data_dir, "patient_df.csv")
    patient_df = pd.read_csv(patient_csv, index_col=0)

    male_pct = (patient_df["SEX"].str.lower() == "male").mean() * 100 if "SEX" in patient_df.columns else 50.0
    medical_pct = 55.0
    elective_pct = 30.0
    over_18_pct = (patient_df["AGE"] >= 18).mean() * 100 if "AGE" in patient_df.columns else 95.0
    over_65_pct = (patient_df["AGE"] >= 65).mean() * 100 if "AGE" in patient_df.columns else 40.0

    ones = np.ones(len(times))
    split = {
        "time": times,
        "male": male_pct * ones,
        "elective": elective_pct * ones,
        "medical": medical_pct * ones,
        "over_18": over_18_pct * ones,
        "over_65": over_65_pct * ones,
    }
    with open(os.path.join(app_data_dir, "forecast_split_random.pkl"), "wb") as f:
        pickle.dump(split, f)


def ensure_data_artefacts(root=None, force=False):
    paths = get_paths(root)
    if not force and check_artefacts_exist(paths):
        return

    print("\n[Bed Allocation] Required data artefacts not found. Generating them now...")
    python = sys.executable

    # Step 1: Generate fake data
    fake_output = os.path.join(paths["FAKE_DATA_DIR"], "fake_data_files")
    if os.path.exists(fake_output):
        shutil.rmtree(fake_output)

    print("  -> Generating fake patient data...")
    subprocess.run(
        [python, "generate_fake_data.py", "-nr", "5000", "-s", "42"],
        cwd=paths["FAKE_DATA_DIR"],
        check=True,
    )

    os.makedirs(paths["DATA_DIR"], exist_ok=True)
    for fname in os.listdir(fake_output):
        src = os.path.join(fake_output, fname)
        dst = os.path.join(paths["DATA_DIR"], fname)
        if os.path.exists(dst):
            os.remove(dst)
        shutil.move(src, dst)
    shutil.rmtree(fake_output)

    # Step 2: Forecast artefacts
    print("  -> Generating synthetic forecast artefacts...")
    generate_synthetic_forecast_artefacts(paths)

    # Step 3: Hospital & wards.csv
    print("  -> Generating virtual hospital and wards specification...")
    subprocess.run(
        [python, "generate_hospital.py"],
        cwd=paths["INTEGRATION_DIR"],
        check=True,
    )

    print("[Bed Allocation] All data artefacts successfully generated!\n")


if __name__ == "__main__":
    ensure_data_artefacts()
