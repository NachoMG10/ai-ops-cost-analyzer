"""
Pydantic models for the AI Ops Cost Analyzer.
Based on the CSV structure: service, region, instance_type, daily_cost, 
usage_cpu_avg, usage_mem_avg, date, status
"""

from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum


class ResourceStatus(str, Enum):
    """Resource status enumeration"""
    ACTIVE = "active"
    IDLE = "idle"
    STOPPED = "stopped"
    TERMINATED = "terminated"


class CostRecord(BaseModel):
    """Model representing a single cost record from CSV"""
    service: str = Field(..., description="Service/resource name")
    region: str = Field(..., description="AWS region")
    instance_type: str = Field(..., description="Instance type or resource type")
    daily_cost: float = Field(..., ge=0, description="Daily cost in USD")
    usage_cpu_avg: str = Field(..., description="Average CPU usage percentage")
    usage_mem_avg: str = Field(..., description="Average memory usage percentage")
    date: date = Field(..., description="Date of the record")
    status: ResourceStatus = Field(..., description="Resource status")

    @field_validator('usage_cpu_avg', 'usage_mem_avg', mode='before')
    @classmethod
    def parse_usage_percentage(cls, v):
        """Parse percentage string to float"""
        if isinstance(v, str):
            # Remove % sign and convert to float
            return float(v.replace('%', ''))
        return float(v)

    model_config = ConfigDict(use_enum_values=True)


class CostRecordResponse(CostRecord):
    """Response model for cost records with computed fields"""
    usage_cpu_avg_float: float = Field(..., description="CPU usage as float")
    usage_mem_avg_float: float = Field(..., description="Memory usage as float")
    monthly_cost_estimate: float = Field(..., description="Estimated monthly cost")
    is_underutilized: bool = Field(..., description="Whether resource is underutilized")
    is_idle: bool = Field(..., description="Whether resource is idle")
    is_high_cost_anomaly: bool = Field(..., description="Whether resource is a high-cost anomaly")

    @classmethod
    def from_cost_record(
        cls,
        record: CostRecord,
        is_underutilized: bool,
        is_idle: bool,
        is_high_cost_anomaly: bool
    ):
        """Create response from CostRecord with analysis flags"""
        cpu_float = float(record.usage_cpu_avg.replace('%', '')) if isinstance(record.usage_cpu_avg, str) else record.usage_cpu_avg
        mem_float = float(record.usage_mem_avg.replace('%', '')) if isinstance(record.usage_mem_avg, str) else record.usage_mem_avg
        
        return cls(
            **record.model_dump(),
            usage_cpu_avg_float=cpu_float,
            usage_mem_avg_float=mem_float,
            monthly_cost_estimate=record.daily_cost * 30,
            is_underutilized=is_underutilized,
            is_idle=is_idle,
            is_high_cost_anomaly=is_high_cost_anomaly
        )


class AnalysisSummary(BaseModel):
    """Summary of cost analysis"""
    total_records: int
    total_daily_cost: float
    total_monthly_cost_estimate: float
    underutilized_count: int
    idle_count: int
    high_cost_anomaly_count: int
    potential_monthly_savings: float = Field(..., description="Estimated potential monthly savings")
    underutilized_resources: List[CostRecordResponse]
    idle_resources: List[CostRecordResponse]
    high_cost_anomalies: List[CostRecordResponse]


class CostSavingsReport(BaseModel):
    """AI-generated cost savings report"""
    summary: str = Field(..., description="Executive summary of the report")
    findings: List[str] = Field(..., description="Key findings")
    recommendations: List[str] = Field(..., description="Actionable recommendations")
    estimated_savings: float = Field(..., description="Estimated total savings per month")
    priority_actions: List[str] = Field(..., description="Priority actions to take")
    analysis_summary: AnalysisSummary


class CSVUploadResponse(BaseModel):
    """Response after CSV upload"""
    message: str
    records_processed: int
    analysis_summary: AnalysisSummary
