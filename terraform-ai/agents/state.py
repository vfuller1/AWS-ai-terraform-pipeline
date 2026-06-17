from __future__ import annotations

from typing import Literal, Optional, TypedDict


class ProvisioningState(TypedDict, total=False):
    """State schema for provisioning workflow."""

    user_request: str
    resource_type: str
    resource_region: str
    resource_tags: dict
    created_by: str
    resource_name: str
    naming_rules: list[str]
    existing_resources: list[dict]
    connectivity_needed: bool
    connectivity_changes: list[str]
    terraform_hcl: str
    terraform_plan_json: str
    plan_status: Literal["success", "failed", "pending"]
    plan_error: Optional[str]
    retry_count: int
    fix_applied: bool
    cost_monthly_delta: float
    cost_breakdown: dict
    pr_url: Optional[str]
    pr_number: Optional[int]
    commit_sha: Optional[str]
    user_decision: Optional[Literal["fix", "abandon"]]
    apply_status: Literal["success", "failed", "pending", "skipped"]
    apply_output: Optional[str]


class DriftState(TypedDict, total=False):
    """State schema for drift detection workflow."""

    drift_detected: bool
    drift_details: list[dict]
    triage_decision: Literal["auto-remediate", "open-pr", "alert-only"]
    remediation_pr_url: Optional[str]
    created_by: str


class DeleteState(TypedDict, total=False):
    """State schema for deletion workflow."""

    user_request: str
    target_resource_name: str
    resource_type: str
    resource_region: str
    created_by: str
    dependency_status: Optional[Literal["block", "warn", "safe"]]
    dependencies_found: list[str]
    cost_savings_monthly: float
    is_production: bool
    typed_confirmation: Optional[str]
    gate1_passed: bool
    gate2_passed: bool
    gate3_passed: bool
    gate4_passed: bool
    destroy_status: Optional[Literal["success", "failed", "pending"]]
    audit_record_url: Optional[str]
    pr_url: Optional[str]
    pr_number: Optional[int]
