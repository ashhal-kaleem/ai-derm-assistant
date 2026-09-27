"""Automated dataset validation suite enforcing zero patient-level data leakage."""

import pandas as pd
import pytest

from src.core.dataset import (
    create_patient_aware_split,
    verify_zero_patient_leakage,
)


def test_verify_zero_patient_leakage_clean():
    """Verify clean splits with disjoint patients pass verification."""
    train_df = pd.DataFrame({
        "lesion_id": ["L1", "L2", "L3"],
        "patient_id": ["P1", "P2", "P3"],
        "dx": ["mel", "nv", "bcc"]
    })
    val_df = pd.DataFrame({
        "lesion_id": ["L4", "L5"],
        "patient_id": ["P4", "P5"],
        "dx": ["bkl", "akiec"]
    })
    
    # Must return True with no error
    is_clean = verify_zero_patient_leakage(train_df, val_df, group_col="patient_id")
    assert is_clean is True


def test_verify_zero_patient_leakage_detects_overlap():
    """Verify overlapping patient IDs trigger ValueError."""
    train_df = pd.DataFrame({
        "lesion_id": ["L1", "L2"],
        "patient_id": ["P1", "P2"],
        "dx": ["mel", "nv"]
    })
    val_df = pd.DataFrame({
        "lesion_id": ["L3", "L4"],
        "patient_id": ["P2", "P3"],  # P2 leaks between train and val
        "dx": ["bkl", "akiec"]
    })
    
    with pytest.raises(AssertionError, match="PATIENT DATA LEAKAGE DETECTED"):
        verify_zero_patient_leakage(train_df, val_df, group_col="patient_id")


def test_create_patient_aware_split():
    """Verify split generation produces balanced folds with zero patient overlap."""
    sample_data = []
    for i in range(100):
        sample_data.append({
            "image_id": f"ISIC_{i:04d}",
            "lesion_id": f"LES_{i // 2:03d}",  # 2 images per lesion
            "patient_id": f"PAT_{i // 2:03d}",
            "dx": ["nv", "mel", "bkl", "bcc", "akiec"][i % 5]
        })
    df = pd.DataFrame(sample_data)
    
    train_df, val_df = create_patient_aware_split(
        df,
        group_col="patient_id",
        target_col="dx",
        val_ratio=0.2,
        seed=42
    )
    
    assert len(train_df) > 0
    assert len(val_df) > 0
    assert verify_zero_patient_leakage(train_df, val_df, group_col="patient_id") is True
