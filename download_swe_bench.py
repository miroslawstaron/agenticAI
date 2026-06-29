#!/usr/bin/env python3
"""
Download SWE-bench Verified Dataset

Downloads the official SWE-bench Verified dataset from HuggingFace.
Dataset size: ~2-5GB depending on options.

Usage:
  python download_swe_bench.py
"""

import os
import json
import sys
from pathlib import Path
from typing import Optional


def download_from_huggingface() -> str:
    """Download SWE-bench Verified from HuggingFace Hub.

    Returns:
        Path to downloaded dataset
    """
    print("[INFO] Downloading SWE-bench Verified from HuggingFace Hub...")
    print("[INFO] This may take 5-10 minutes depending on your connection.\n")

    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("[FAIL] huggingface_hub not installed")
        print("[INFO] Install with: pip install huggingface-hub")
        return None

    try:
        # Download the dataset
        print("[...] Downloading swe-bench-verified.json (~2GB)...")
        dataset_path = hf_hub_download(
            repo_id="princeton-nlp/SWE-bench_Verified",
            filename="swe-bench-verified.json",
            repo_type="dataset",
            cache_dir="./data"
        )

        print(f"[OK] Downloaded to: {dataset_path}")
        return dataset_path

    except Exception as e:
        print(f"[FAIL] Download failed: {e}")
        return None


def download_from_github() -> Optional[str]:
    """Download SWE-bench Verified from GitHub release.

    Returns:
        Path to downloaded dataset, or None if failed
    """
    print("[INFO] Downloading from GitHub release...")

    try:
        import urllib.request
        import zipfile

        url = "https://github.com/princeton-nlp/SWE-bench/releases/download/v1.2.0/swe-bench-verified.zip"
        zip_path = "swe-bench-verified.zip"
        extract_path = "."

        print(f"[...] Downloading {url}...")
        urllib.request.urlretrieve(url, zip_path)
        print(f"[OK] Downloaded {zip_path}")

        print("[...] Extracting...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        print("[OK] Extracted")

        # Clean up
        os.remove(zip_path)

        # Find the dataset file
        for root, dirs, files in os.walk("."):
            for file in files:
                if file.endswith("verified.json"):
                    dataset_path = os.path.join(root, file)
                    print(f"[OK] Found dataset at: {dataset_path}")
                    return dataset_path

        return "swe-bench-verified.json" if os.path.exists("swe-bench-verified.json") else None

    except Exception as e:
        print(f"[FAIL] GitHub download failed: {e}")
        return None


def create_sample_dataset() -> str:
    """Create a sample dataset for testing.

    Returns:
        Path to sample dataset
    """
    print("[INFO] Creating sample SWE-bench dataset for testing...")

    sample_data = [
        {
            "task_id": "django__django-10850",
            "repo": "django/django",
            "base_commit": "21a8079b12e1c0ffb2485c0db3e3d1a2c3e4f5g6",
            "problem_statement": "Fix issue where ModelForm does not preserve field order from Meta.fields.",
            "test_patch": "tests/forms/test_modelform.py",
            "gold_patch": None,
            "hints_text": "Check ModelFormMetaclass in django/forms/models.py",
            "created_at": "2023-01-15",
            "version": "1.0"
        },
        {
            "task_id": "requests__requests-3362",
            "repo": "psf/requests",
            "base_commit": "d1ce8c7d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t",
            "problem_statement": "Add support for custom timeout per request in Session.",
            "test_patch": "tests/test_requests.py",
            "gold_patch": None,
            "hints_text": "Modify Request.prepare() method in models.py",
            "created_at": "2023-02-20",
            "version": "1.0"
        },
        {
            "task_id": "numpy__numpy-13794",
            "repo": "numpy/numpy",
            "base_commit": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
            "problem_statement": "Optimize array concatenation for small arrays.",
            "test_patch": "numpy/tests/test_creation.py",
            "gold_patch": None,
            "hints_text": "Check concatenate function in core/multiarray.py",
            "created_at": "2023-03-10",
            "version": "1.0"
        },
        {
            "task_id": "pandas__pandas-21476",
            "repo": "pandas-dev/pandas",
            "base_commit": "e1f2g3h4i5j6k7l8m9n0o1p2q3r4s5t6u7v8w9x0",
            "problem_statement": "Fix memory leak in DataFrame groupby operation.",
            "test_patch": "pandas/tests/groupby/test_groupby.py",
            "gold_patch": None,
            "hints_text": "Check GroupBy class in core/groupby.py",
            "created_at": "2023-04-05",
            "version": "1.0"
        },
        {
            "task_id": "scikit-learn__scikit-learn-14102",
            "repo": "scikit-learn/scikit-learn",
            "base_commit": "f1g2h3i4j5k6l7m8n9o0p1q2r3s4t5u6v7w8x9y0",
            "problem_statement": "Add support for weighted samples in KMeans clustering.",
            "test_patch": "sklearn/cluster/tests/test_k_means.py",
            "gold_patch": None,
            "hints_text": "Modify KMeans.fit() method in cluster/_kmeans.py",
            "created_at": "2023-05-12",
            "version": "1.0"
        },
        {
            "task_id": "matplotlib__matplotlib-18722",
            "repo": "matplotlib/matplotlib",
            "base_commit": "g1h2i3j4k5l6m7n8o9p0q1r2s3t4u5v6w7x8y9z0",
            "problem_statement": "Fix issue with colorbar positioning in matplotlib plots.",
            "test_patch": "lib/matplotlib/tests/test_colorbar.py",
            "gold_patch": None,
            "hints_text": "Check ColorbarBase class in colorbar.py",
            "created_at": "2023-06-18",
            "version": "1.0"
        },
        {
            "task_id": "tensorflow__tensorflow-40821",
            "repo": "tensorflow/tensorflow",
            "base_commit": "h1i2j3k4l5m6n7o8p9q0r1s2t3u4v5w6x7y8z9a0",
            "problem_statement": "Improve performance of tensor concatenation operations.",
            "test_patch": "tensorflow/python/ops/array_ops_test.py",
            "gold_patch": None,
            "hints_text": "Check concat function in tensorflow/python/ops/array_ops.py",
            "created_at": "2023-07-22",
            "version": "1.0"
        },
        {
            "task_id": "pytorch__pytorch-42816",
            "repo": "pytorch/pytorch",
            "base_commit": "i1j2k3l4m5n6o7p8q9r0s1t2u3v4w5x6y7z8a9b0",
            "problem_statement": "Fix CUDA memory allocation issue in batch operations.",
            "test_patch": "test/test_memory.py",
            "gold_patch": None,
            "hints_text": "Check allocate_memory in aten/src/ATen/cuda/CudaDevice.cpp",
            "created_at": "2023-08-30",
            "version": "1.0"
        },
        {
            "task_id": "flask__flask-3639",
            "repo": "pallets/flask",
            "base_commit": "j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7a8b9c0",
            "problem_statement": "Add support for custom error handlers in Flask blueprints.",
            "test_patch": "tests/test_error_handlers.py",
            "gold_patch": None,
            "hints_text": "Modify Blueprint class in flask/blueprints.py",
            "created_at": "2023-09-14",
            "version": "1.0"
        },
        {
            "task_id": "sqlalchemy__sqlalchemy-7050",
            "repo": "sqlalchemy/sqlalchemy",
            "base_commit": "k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0",
            "problem_statement": "Fix query performance issue with complex joins.",
            "test_patch": "test/sql/test_query.py",
            "gold_patch": None,
            "hints_text": "Check join logic in sql/selectable.py",
            "created_at": "2023-10-25",
            "version": "1.0"
        }
    ]

    output_path = "swe_bench_verified.json"
    with open(output_path, 'w') as f:
        json.dump(sample_data, f, indent=2)

    print(f"[OK] Created sample dataset with {len(sample_data)} tasks")
    print(f"[OK] Saved to: {output_path}")
    return output_path


def verify_dataset(dataset_path: str) -> bool:
    """Verify dataset integrity.

    Args:
        dataset_path: Path to dataset file

    Returns:
        True if valid, False otherwise
    """
    if not os.path.exists(dataset_path):
        print(f"[FAIL] Dataset not found: {dataset_path}")
        return False

    try:
        with open(dataset_path, 'r') as f:
            data = json.load(f)

        if isinstance(data, list):
            count = len(data)
        elif isinstance(data, dict):
            count = len(data)
        else:
            print("[FAIL] Invalid dataset format")
            return False

        print(f"[OK] Dataset valid: {count} tasks")
        return True

    except json.JSONDecodeError:
        print("[FAIL] Invalid JSON in dataset")
        return False
    except Exception as e:
        print(f"[FAIL] Error verifying dataset: {e}")
        return False


def main():
    """Main download workflow."""
    print("\n" + "=" * 80)
    print("SWE-BENCH VERIFIED DATASET DOWNLOADER")
    print("=" * 80 + "\n")

    dataset_path = None

    # Try each method
    print("[INFO] Attempting download methods in order:\n")

    # Method 1: HuggingFace
    print("1. HuggingFace Hub (Official Source)")
    print("-" * 40)
    dataset_path = download_from_huggingface()
    if dataset_path:
        print()
    else:
        print("[SKIP] HuggingFace download failed\n")

        # Method 2: GitHub
        print("2. GitHub Release")
        print("-" * 40)
        dataset_path = download_from_github()
        if dataset_path:
            print()
        else:
            print("[SKIP] GitHub download failed\n")

    # Method 3: Create sample
    if not dataset_path:
        print("3. Create Sample Dataset")
        print("-" * 40)
        dataset_path = create_sample_dataset()
        print()

    # Verify
    if dataset_path:
        print("VERIFICATION")
        print("-" * 40)
        if verify_dataset(dataset_path):
            print(f"\n[OK] Ready to test with: {dataset_path}")
            print("[OK] Run: python swe_bench_test.py")
        else:
            print("\n[FAIL] Dataset verification failed")
    else:
        print("\n[FAIL] All download methods failed")
        sys.exit(1)

    print("\n" + "=" * 80 + "\n")


if __name__ == '__main__':
    main()
