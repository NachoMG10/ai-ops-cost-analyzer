"""
Cost analysis logic for detecting underutilized resources, 
idle resources, and high-cost anomalies.
"""

from typing import List, Tuple
from app.models import CostRecord, CostRecordResponse, AnalysisSummary


class CostAnalyzer:
    """Analyzer for cloud cost data"""
    
    # Thresholds for analysis
    UNDERUTILIZED_CPU_THRESHOLD = 20.0  # CPU usage below 20%
    UNDERUTILIZED_MEM_THRESHOLD = 20.0  # Memory usage below 20%
    IDLE_CPU_THRESHOLD = 5.0  # CPU usage below 5% considered idle
    IDLE_MEM_THRESHOLD = 5.0  # Memory usage below 5% considered idle
    HIGH_COST_MULTIPLIER = 2.0  # Cost > 2x average is anomaly
    SAVINGS_ESTIMATE_UNDERUTILIZED = 0.3  # 30% savings potential
    SAVINGS_ESTIMATE_IDLE = 0.8  # 80% savings potential (can be stopped)
    SAVINGS_ESTIMATE_ANOMALY = 0.2  # 20% savings potential (optimization)

    @staticmethod
    def parse_usage_percentage(usage_str: str) -> float:
        """Parse percentage string to float"""
        if isinstance(usage_str, str):
            return float(usage_str.replace('%', ''))
        return float(usage_str)

    @classmethod
    def is_underutilized(cls, record: CostRecord) -> bool:
        """
        Check if resource is underutilized.
        Criteria: CPU < 20% AND Memory < 20% AND status is active
        """
        cpu = cls.parse_usage_percentage(record.usage_cpu_avg)
        mem = cls.parse_usage_percentage(record.usage_mem_avg)
        
        return (
            record.status == "active" and
            cpu < cls.UNDERUTILIZED_CPU_THRESHOLD and
            mem < cls.UNDERUTILIZED_MEM_THRESHOLD
        )

    @classmethod
    def is_idle(cls, record: CostRecord) -> bool:
        """
        Check if resource is idle.
        Criteria: status is 'idle' OR (CPU < 5% AND Memory < 5%)
        """
        if record.status == "idle":
            return True
        
        cpu = cls.parse_usage_percentage(record.usage_cpu_avg)
        mem = cls.parse_usage_percentage(record.usage_mem_avg)
        
        return (
            cpu < cls.IDLE_CPU_THRESHOLD and
            mem < cls.IDLE_MEM_THRESHOLD
        )

    @classmethod
    def is_high_cost_anomaly(cls, record: CostRecord, avg_cost: float) -> bool:
        """
        Check if resource is a high-cost anomaly.
        Criteria: daily_cost > 2x average cost
        """
        return record.daily_cost > (avg_cost * cls.HIGH_COST_MULTIPLIER)

    @classmethod
    def analyze_records(cls, records: List[CostRecord]) -> AnalysisSummary:
        """
        Analyze cost records and generate summary.
        
        Args:
            records: List of cost records to analyze
            
        Returns:
            AnalysisSummary with findings
        """
        if not records:
            return AnalysisSummary(
                total_records=0,
                total_daily_cost=0.0,
                total_monthly_cost_estimate=0.0,
                underutilized_count=0,
                idle_count=0,
                high_cost_anomaly_count=0,
                potential_monthly_savings=0.0,
                underutilized_resources=[],
                idle_resources=[],
                high_cost_anomalies=[]
            )

        # Calculate average cost
        total_daily_cost = sum(r.daily_cost for r in records)
        avg_cost = total_daily_cost / len(records)

        # Analyze each record
        underutilized = []
        idle = []
        anomalies = []

        for record in records:
            is_underutilized = cls.is_underutilized(record)
            is_idle = cls.is_idle(record)
            is_anomaly = cls.is_high_cost_anomaly(record, avg_cost)

            response = CostRecordResponse.from_cost_record(
                record,
                is_underutilized,
                is_idle,
                is_anomaly
            )

            if is_underutilized:
                underutilized.append(response)
            if is_idle:
                idle.append(response)
            if is_anomaly:
                anomalies.append(response)

        # Calculate potential savings
        potential_savings = 0.0
        
        # Savings from underutilized resources (can downsize)
        for resource in underutilized:
            if not resource.is_idle:  # Don't double-count
                potential_savings += resource.monthly_cost_estimate * cls.SAVINGS_ESTIMATE_UNDERUTILIZED
        
        # Savings from idle resources (can stop/terminate)
        for resource in idle:
            potential_savings += resource.monthly_cost_estimate * cls.SAVINGS_ESTIMATE_IDLE
        
        # Savings from high-cost anomalies (optimization opportunities)
        for resource in anomalies:
            if not resource.is_idle and not resource.is_underutilized:  # Don't double-count
                potential_savings += resource.monthly_cost_estimate * cls.SAVINGS_ESTIMATE_ANOMALY

        return AnalysisSummary(
            total_records=len(records),
            total_daily_cost=total_daily_cost,
            total_monthly_cost_estimate=total_daily_cost * 30,
            underutilized_count=len(underutilized),
            idle_count=len(idle),
            high_cost_anomaly_count=len(anomalies),
            potential_monthly_savings=potential_savings,
            underutilized_resources=underutilized,
            idle_resources=idle,
            high_cost_anomalies=anomalies
        )
