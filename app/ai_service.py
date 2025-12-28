"""
AI service for generating cost savings reports using OpenAI.
Supports both real OpenAI API and mock mode for testing.
"""

import os
from typing import Optional
from app.models import AnalysisSummary, CostSavingsReport


class AIService:
    """Service for AI-powered report generation"""
    
    def __init__(self, use_mock: bool = False, api_key: Optional[str] = None):
        """
        Initialize AI service.
        
        Args:
            use_mock: If True, use mock responses instead of OpenAI API
            api_key: OpenAI API key (if None, will try to get from env)
        """
        self.use_mock = use_mock
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if not use_mock and not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY env var or use_mock=True"
            )
        
        if not use_mock:
            try:
                import openai
                self.client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "openai package required. Install with: pip install openai"
                )

    def generate_cost_savings_report(
        self,
        analysis_summary: AnalysisSummary
    ) -> CostSavingsReport:
        """
        Generate AI-powered cost savings report.
        
        Args:
            analysis_summary: Analysis summary with findings
            
        Returns:
            CostSavingsReport with AI-generated insights
        """
        if self.use_mock:
            return self._generate_mock_report(analysis_summary)
        else:
            return self._generate_openai_report(analysis_summary)

    def _generate_mock_report(
        self,
        analysis_summary: AnalysisSummary
    ) -> CostSavingsReport:
        """Generate mock report for testing"""
        
        summary_text = (
            f"Analysis of {analysis_summary.total_records} cloud resources reveals "
            f"significant cost optimization opportunities. Current monthly spend is "
            f"${analysis_summary.total_monthly_cost_estimate:,.2f}, with potential "
            f"savings of ${analysis_summary.potential_monthly_savings:,.2f} per month."
        )
        
        findings = []
        if analysis_summary.idle_count > 0:
            findings.append(
                f"Found {analysis_summary.idle_count} idle resources that can be "
                f"stopped or terminated, saving approximately "
                f"${sum(r.monthly_cost_estimate * 0.8 for r in analysis_summary.idle_resources):,.2f}/month"
            )
        if analysis_summary.underutilized_count > 0:
            findings.append(
                f"Identified {analysis_summary.underutilized_count} underutilized "
                f"resources that can be downsized to smaller instance types."
            )
        if analysis_summary.high_cost_anomaly_count > 0:
            findings.append(
                f"Detected {analysis_summary.high_cost_anomaly_count} high-cost "
                f"anomalies requiring optimization review."
            )
        
        recommendations = []
        if analysis_summary.idle_resources:
            recommendations.append(
                "Immediately stop or terminate idle resources, especially: " +
                ", ".join([r.service for r in analysis_summary.idle_resources[:3]])
            )
        if analysis_summary.underutilized_resources:
            recommendations.append(
                "Downsize underutilized resources to smaller instance types. "
                "Consider right-sizing based on actual usage patterns."
            )
        if analysis_summary.high_cost_anomalies:
            recommendations.append(
                "Review high-cost resources for optimization opportunities. "
                "Consider reserved instances or spot instances where appropriate."
            )
        recommendations.append(
            "Implement automated resource scheduling for non-production environments."
        )
        recommendations.append(
            "Set up cost alerts and budgets to prevent future cost anomalies."
        )
        
        priority_actions = []
        if analysis_summary.idle_resources:
            priority_actions.append(
                f"Terminate {len(analysis_summary.idle_resources)} idle resources "
                f"(highest impact: ${sum(r.monthly_cost_estimate * 0.8 for r in analysis_summary.idle_resources):,.2f}/month savings)"
            )
        if analysis_summary.underutilized_resources:
            priority_actions.append(
                f"Right-size {len(analysis_summary.underutilized_resources)} "
                f"underutilized resources"
            )
        if analysis_summary.high_cost_anomalies:
            priority_actions.append(
                f"Review and optimize {len(analysis_summary.high_cost_anomalies)} "
                f"high-cost resources"
            )
        
        return CostSavingsReport(
            summary=summary_text,
            findings=findings,
            recommendations=recommendations,
            estimated_savings=analysis_summary.potential_monthly_savings,
            priority_actions=priority_actions,
            analysis_summary=analysis_summary
        )

    def _generate_openai_report(
        self,
        analysis_summary: AnalysisSummary
    ) -> CostSavingsReport:
        """Generate report using OpenAI API"""
        
        # Build prompt
        prompt = self._build_prompt(analysis_summary)
        
        # Call OpenAI API
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior DevOps and cloud cost optimization expert. "
                        "Analyze cloud cost data and provide actionable recommendations "
                        "for cost savings. Be specific, data-driven, and prioritize "
                        "high-impact actions."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        # Parse response (simplified - in production, use structured output)
        ai_response = response.choices[0].message.content
        
        # For now, extract structured data from AI response
        # In production, use OpenAI's structured outputs or function calling
        return self._parse_ai_response(ai_response, analysis_summary)

    def _build_prompt(self, analysis_summary: AnalysisSummary) -> str:
        """Build prompt for OpenAI"""
        prompt = f"""
Analyze the following cloud cost data and generate a comprehensive cost savings report.

Summary:
- Total Resources: {analysis_summary.total_records}
- Total Daily Cost: ${analysis_summary.total_daily_cost:,.2f}
- Total Monthly Cost Estimate: ${analysis_summary.total_monthly_cost_estimate:,.2f}
- Potential Monthly Savings: ${analysis_summary.potential_monthly_savings:,.2f}

Findings:
- Underutilized Resources: {analysis_summary.underutilized_count}
- Idle Resources: {analysis_summary.idle_count}
- High-Cost Anomalies: {analysis_summary.high_cost_anomaly_count}

Underutilized Resources:
"""
        for resource in analysis_summary.underutilized_resources[:5]:
            prompt += f"- {resource.service} ({resource.instance_type}): "
            prompt += f"CPU {resource.usage_cpu_avg_float}%, "
            prompt += f"Memory {resource.usage_mem_avg_float}%, "
            prompt += f"Cost: ${resource.daily_cost}/day\n"

        prompt += "\nIdle Resources:\n"
        for resource in analysis_summary.idle_resources[:5]:
            prompt += f"- {resource.service} ({resource.instance_type}): "
            prompt += f"Status: {resource.status}, "
            prompt += f"Cost: ${resource.daily_cost}/day\n"

        prompt += "\nHigh-Cost Anomalies:\n"
        for resource in analysis_summary.high_cost_anomalies[:5]:
            prompt += f"- {resource.service} ({resource.instance_type}): "
            prompt += f"Cost: ${resource.daily_cost}/day\n"

        prompt += """
Please provide:
1. Executive summary (2-3 sentences)
2. Key findings (bullet points)
3. Actionable recommendations (prioritized)
4. Priority actions (top 3-5 actions to take immediately)

Format your response in a structured way that can be parsed.
"""
        return prompt

    def _parse_ai_response(
        self,
        ai_response: str,
        analysis_summary: AnalysisSummary
    ) -> CostSavingsReport:
        """Parse AI response into structured report"""
        # Simplified parsing - in production, use structured outputs
        lines = ai_response.split('\n')
        
        # Extract summary (first paragraph)
        summary = ""
        findings = []
        recommendations = []
        priority_actions = []
        
        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if 'summary' in line.lower() or 'executive' in line.lower():
                current_section = 'summary'
            elif 'finding' in line.lower():
                current_section = 'findings'
            elif 'recommendation' in line.lower():
                current_section = 'recommendations'
            elif 'priority' in line.lower() or 'action' in line.lower():
                current_section = 'priority'
            elif line.startswith('-') or line.startswith('•') or line.startswith('*'):
                item = line.lstrip('-•* ').strip()
                if current_section == 'findings':
                    findings.append(item)
                elif current_section == 'recommendations':
                    recommendations.append(item)
                elif current_section == 'priority':
                    priority_actions.append(item)
            elif current_section == 'summary' and not summary:
                summary = line
        
        # Fallback to mock if parsing fails
        if not summary or not findings:
            return self._generate_mock_report(analysis_summary)
        
        return CostSavingsReport(
            summary=summary or f"Analysis of {analysis_summary.total_records} resources.",
            findings=findings[:10] or ["Review cost data for optimization opportunities"],
            recommendations=recommendations[:10] or ["Implement cost monitoring"],
            estimated_savings=analysis_summary.potential_monthly_savings,
            priority_actions=priority_actions[:5] or ["Review findings"],
            analysis_summary=analysis_summary
        )
