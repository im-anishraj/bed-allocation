"""
All-in-one setup script: generates fake data, creates all required
data artefacts (including synthetic forecast data), builds the virtual
hospital, and launches the Dash UI.

This replaces the bash-only integration_test.sh pipeline with a
cross-platform Python equivalent that runs entirely within the Docker
container.
"""

import os
import sys
import shutil
import subprocess
import pickle

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
APP_DATA_DIR = os.path.join(ROOT, "app", "app", "data")
FAKE_DATA_DIR = os.path.join(ROOT, "fake_data_generation")
INTEGRATION_DIR = os.path.join(ROOT, "tests", "integration")


def run_step(description, cmd, cwd=None):
    """Run a subprocess step with error handling."""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}\n")
    result = subprocess.run(
        cmd, cwd=cwd or ROOT, shell=False,
        stdout=sys.stdout, stderr=sys.stderr
    )
    if result.returncode != 0:
        print(f"\nERROR: {description} failed with exit code {result.returncode}")
        sys.exit(1)
    print(f"\n  >> {description} completed successfully")


def generate_synthetic_forecast_artefacts():
    """
    Generate synthetic forecast data artefacts that match the structure
    expected by the Dash UI, without running the expensive MCMC model.
    
    This creates:
      - data/forecast_results.pkl
      - app/app/data/forecast_percentiles.pkl
      - app/app/data/forecast_aggregated_percentiles.pkl
      - app/app/data/forecast_split_random.pkl
    """
    from forecasting.utils import START_FORECAST, HISTORIC_HOURS, FORECAST_HOURS, HOURS_IN_WEEK

    print("\n" + "=" * 60)
    print("  Generating synthetic forecast artefacts (skipping MCMC)")
    print("=" * 60 + "\n")

    # Create time index matching the expected forecast window
    n_hours = HISTORIC_HOURS + HOURS_IN_WEEK + FORECAST_HOURS  # 168 + 168 + 24 = 360
    start = START_FORECAST - pd.Timedelta(hours=HISTORIC_HOURS)
    times = pd.date_range(start, periods=n_hours, freq="h")

    # Generate synthetic posterior samples (shape: n_samples x n_hours)
    rng = np.random.RandomState(42)
    n_samples = 100
    # Simulate hourly admissions as Poisson-like data with time-of-day pattern
    hour_pattern = np.array([
        0.5, 0.3, 0.2, 0.2, 0.3, 0.5, 1.0, 1.8, 2.5, 3.0, 3.2, 3.0,
        2.8, 2.5, 2.2, 2.0, 1.8, 1.5, 1.2, 1.0, 0.8, 0.7, 0.6, 0.5
    ])
    base_rates = np.tile(hour_pattern, n_hours // 24 + 1)[:n_hours]
    posterior = np.array([
        rng.poisson(lam=base_rates) for _ in range(n_samples)
    ]).astype(float)

    # Save forecast_results.pkl (matches forecast.call_forecast output)
    forecast_results = {
        "time": times,
        "posterior": posterior,
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "forecast_results.pkl"), "wb") as f:
        pickle.dump(forecast_results, f)
    print("  >> Saved data/forecast_results.pkl")

    # Create app data directory
    os.makedirs(APP_DATA_DIR, exist_ok=True)

    # Calculate percentiles
    lower = np.percentile(posterior, 5, axis=0)
    upper = np.percentile(posterior, 95, axis=0)
    median_vals = np.percentile(posterior, 50, axis=0)

    # api.py expects PERCENTILES["percentiles"] as shape (3, n_times):
    #   row 0 = 5th percentile, row 1 = median, row 2 = 95th percentile
    percentiles_array = np.array([lower, median_vals, upper])

    percentiles = {
        "time": times,
        "percentiles": percentiles_array,
    }
    with open(os.path.join(APP_DATA_DIR, "forecast_percentiles.pkl"), "wb") as f:
        pickle.dump(percentiles, f)
    print("  >> Saved app/app/data/forecast_percentiles.pkl")

    # forecast.py component expects AGG_PERCENTILES with lower/upper keys
    aggregated = {
        "time": times,
        "lower": lower,
        "upper": upper,
        "median": median_vals,
    }
    with open(os.path.join(APP_DATA_DIR, "forecast_aggregated_percentiles.pkl"), "wb") as f:
        pickle.dump(aggregated, f)
    print("  >> Saved app/app/data/forecast_aggregated_percentiles.pkl")

    # Load patient data to calculate realistic splits
    patient_csv = os.path.join(DATA_DIR, "patient_df.csv")
    patient_df = pd.read_csv(patient_csv, index_col=0)

    # Calculate percentages from the patient data
    male_pct = (patient_df["SEX"].str.lower() == "male").mean() * 100 if "SEX" in patient_df.columns else 50.0
    
    # Check for medical/surgical distinction
    if "IS_MEDICAL" in patient_df.columns:
        medical_pct = patient_df["IS_MEDICAL"].mean() * 100
    elif "DEPARTMENT" in patient_df.columns:
        medical_pct = (patient_df["DEPARTMENT"].str.lower() == "medical").mean() * 100
    else:
        medical_pct = 55.0

    if "ADMISSION_TYPE" in patient_df.columns:
        elective_pct = (patient_df["ADMISSION_TYPE"].str.lower() == "elective").mean() * 100
    elif "ELECTIVE" in patient_df.columns:
        if patient_df["ELECTIVE"].dtype == object:
            elective_pct = (patient_df["ELECTIVE"].str.lower() == "yes").mean() * 100
        else:
            elective_pct = patient_df["ELECTIVE"].mean() * 100
    else:
        elective_pct = 30.0

    over_18_pct = (patient_df["AGE"] >= 18).mean() * 100 if "AGE" in patient_df.columns else 95.0
    over_65_pct = (patient_df["AGE"] >= 65).mean() * 100 if "AGE" in patient_df.columns else 40.0

    # Create arrays matching the time dimension
    ones = np.ones(len(times))
    split = {
        "time": times,
        "male": male_pct * ones,
        "elective": elective_pct * ones,
        "medical": medical_pct * ones,
        "over_18": over_18_pct * ones,
        "over_65": over_65_pct * ones,
    }
    with open(os.path.join(APP_DATA_DIR, "forecast_split_random.pkl"), "wb") as f:
        pickle.dump(split, f)
    print("  >> Saved app/app/data/forecast_split_random.pkl")

    print("\n  >> All forecast artefacts generated successfully")


def main():
    python = sys.executable

    # ----- Step 1: Generate fake data -----
    fake_output = os.path.join(FAKE_DATA_DIR, "fake_data_files")
    if os.path.exists(fake_output):
        shutil.rmtree(fake_output)

    run_step(
        "Step 1/4: Generating fake patient data (20,000 records)",
        [python, "generate_fake_data.py", "-nr", "20000", "-s", "42"],
        cwd=FAKE_DATA_DIR,
    )

    # Move generated files to data/
    os.makedirs(DATA_DIR, exist_ok=True)
    for fname in os.listdir(fake_output):
        src = os.path.join(fake_output, fname)
        dst = os.path.join(DATA_DIR, fname)
        if os.path.exists(dst):
            os.remove(dst)
        shutil.move(src, dst)
    shutil.rmtree(fake_output)
    print(f"  >> Moved fake data files to {DATA_DIR}")

    # ----- Step 2: Generate synthetic forecast artefacts -----
    generate_synthetic_forecast_artefacts()

    # ----- Step 3: Generate virtual hospital -----
    run_step(
        "Step 3/4: Creating virtual hospital",
        [python, "generate_hospital.py"],
        cwd=INTEGRATION_DIR,
    )

    # ----- Step 4: Launch UI -----
    print(f"\n{'='*60}")
    print("  Step 4/4: Launching the Bed Allocation UI")
    print(f"{'='*60}\n")
    print("=" * 60)
    print("  The application is available at: http://localhost:8888")
    print("=" * 60)
    print("\nPress Ctrl+C to stop the server.\n")

    subprocess.run(
        [python, os.path.join(ROOT, "app", "run.py")],
        cwd=ROOT,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )


if __name__ == "__main__":
    main()
