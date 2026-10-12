"""Dataset Partitioning and Patient-Aware Leakage Prevention Engine."""

from typing import Dict, List, Set, Tuple
import pandas as pd


def verify_zero_patient_leakage(train_df: pd.DataFrame, val_df: pd.DataFrame, group_col: str = "lesion_id") -> bool:
    """Assert that zero lesion/patient identifiers overlap between train and validation partitions.
    
    Raises:
        AssertionError: If any group identifier intersects between splits.
    """
    train_groups: Set[str] = set(train_df[group_col].dropna().unique())
    val_groups: Set[str] = set(val_df[group_col].dropna().unique())
    leakage = train_groups.intersection(val_groups)
    
    if len(leakage) > 0:
        raise AssertionError(f"PATIENT DATA LEAKAGE DETECTED: {len(leakage)} lesions overlap across splits!")
    return True


def create_patient_aware_split(
    df: pd.DataFrame,
    group_col: str = "lesion_id",
    target_col: str = "dx",
    val_ratio: float = 0.2,
    seed: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Partition dataset by grouping strictly on lesion_id with balanced class distribution.
    
    Ensures multi-image lesions never appear in both train and validation sets.
    """
    # Group by lesion_id and assign dominant diagnosis per lesion
    lesion_summary = df.groupby(group_col)[target_col].agg(lambda x: x.mode()[0]).reset_index()
    
    # Stratify unique lesions
    classes = lesion_summary[target_col].unique()
    val_lesions: List[str] = []
    
    for cls in sorted(classes):
        cls_lesions = lesion_summary[lesion_summary[target_col] == cls][group_col].sample(
            frac=val_ratio, random_state=seed
        ).tolist()
        val_lesions.extend(cls_lesions)
        
    val_set = set(val_lesions)
    val_mask = df[group_col].isin(val_set)
    val_df = df[val_mask].copy()
    train_df = df[~val_mask].copy()
    
    verify_zero_patient_leakage(train_df, val_df, group_col=group_col)
    return train_df, val_df
