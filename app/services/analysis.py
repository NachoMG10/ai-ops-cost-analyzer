"""
Business Logic: Waste Detection Service
This module implements rule-based waste detection using Pandas DataFrames.
Waste is defined as resources that are either:
1. Idle (status == 'idle')
2. Extremely underutilized (CPU usage < 5%)

These resources are prime candidates for termination or shutdown to reduce costs.
"""

import pandas as pd
import os
from typing import Dict, Any, Optional
from pathlib import Path


def load_csv_to_dataframe(csv_path: str) -> pd.DataFrame:
    """
    Business Logic: Load CSV cost data into Pandas DataFrame for analysis.
    
    This function reads the cost data CSV file and converts it into a DataFrame
    for efficient data manipulation and analysis.
    
    Args:
        csv_path: Path to the CSV file
        
    Returns:
        DataFrame with cost data
    """
    try:
        df = pd.read_csv(csv_path)
        return df
    except Exception as e:
        raise ValueError(f"Error loading CSV file: {str(e)}")


def parse_usage_percentage(usage_str: str) -> float:
    """
    Business Logic: Parse percentage strings to numeric values.
    
    Handles percentage values that may be stored as strings (e.g., "12%", "5%")
    and converts them to float for mathematical operations.
    
    Args:
        usage_str: Percentage string (e.g., "12%" or "12")
        
    Returns:
        Float value of the percentage
    """
    if isinstance(usage_str, str):
        return float(usage_str.replace('%', ''))
    return float(usage_str)


def detect_waste(df: pd.DataFrame) -> pd.DataFrame:
    """
    Business Logic: Rule-based waste detection algorithm.
    
    This function implements the core business logic for identifying wasteful resources:
    - Resources with status == 'idle' are considered waste (not generating value)
    - Resources with CPU usage < 5% are considered waste (extremely underutilized)
    
    These rules are based on industry best practices where resources consuming
    less than 5% CPU are typically not providing meaningful value and can be
    safely terminated or stopped to reduce cloud costs.
    
    Args:
        df: DataFrame with cost data containing columns:
            - usage_cpu_avg: CPU usage percentage (string or numeric)
            - status: Resource status (string)
            
    Returns:
        DataFrame with additional 'is_waste' boolean column indicating
        which resources are flagged as waste
    """
    # Create a copy to avoid modifying the original DataFrame
    df_result = df.copy()
    
    # Business Logic: Parse CPU usage to numeric if it's a string
    df_result['cpu_usage_numeric'] = df_result['usage_cpu_avg'].apply(parse_usage_percentage)
    
    # Business Logic: Rule 1 - Flag resources with status == 'idle'
    # Idle resources are not serving any purpose and should be terminated
    is_idle = df_result['status'].str.lower() == 'idle'
    
    # Business Logic: Rule 2 - Flag resources with CPU usage < 5%
    # Resources using less than 5% CPU are extremely underutilized and
    # likely candidates for downsizing or termination
    low_cpu = df_result['cpu_usage_numeric'] < 5.0
    
    # Business Logic: Combine rules - a resource is waste if it meets either condition
    df_result['is_waste'] = is_idle | low_cpu
    
    return df_result


def get_waste_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Business Logic: Generate summary statistics for waste detection.
    
    Calculates key metrics to understand the financial impact of wasteful resources:
    - Total number of wasteful resources
    - Total daily cost of waste
    - Estimated monthly waste cost
    - List of wasteful resources with details
    
    Args:
        df: DataFrame with 'is_waste' column from detect_waste()
        
    Returns:
        Dictionary with waste summary statistics
    """
    waste_df = df[df['is_waste'] == True].copy()
    
    total_waste_count = len(waste_df)
    total_daily_waste_cost = waste_df['daily_cost'].sum() if total_waste_count > 0 else 0.0
    estimated_monthly_waste = total_daily_waste_cost * 30
    
    # Convert waste rows to list of dictionaries for API response
    waste_resources = waste_df.to_dict('records') if total_waste_count > 0 else []
    
    return {
        'waste_count': total_waste_count,
        'total_daily_waste_cost': float(total_daily_waste_cost),
        'estimated_monthly_waste': float(estimated_monthly_waste),
        'waste_resources': waste_resources,
        'total_resources': len(df)
    }


def generate_openai_waste_summary(waste_df: pd.DataFrame, api_key: Optional[str] = None) -> str:
    """
    Business Logic: Generate natural language summary of waste using OpenAI.
    
    This function takes the flagged waste resources and generates a human-readable
    summary suggesting which resources to turn off. The AI analyzes the waste data
    and provides actionable recommendations.
    
    If OpenAI API key is not available, returns a mock response to ensure
    the application doesn't crash in development/testing environments.
    
    Args:
        waste_df: DataFrame containing only the wasteful resources
        api_key: Optional OpenAI API key. If None, uses environment variable or mock.
        
    Returns:
        Natural language summary string with recommendations
    """
    # Get API key from parameter or environment
    if api_key is None:
        api_key = os.getenv("OPENAI_API_KEY")
    
    # Business Logic: If no API key, return mock response for development/testing
    if not api_key:
        return _generate_mock_waste_summary(waste_df)
    
    # Business Logic: Use OpenAI to generate intelligent waste summary
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        
        # Build prompt with waste data
        prompt = _build_waste_analysis_prompt(waste_df)
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a cloud cost optimization expert. Analyze the provided "
                        "wasteful cloud resources and generate a concise, actionable summary "
                        "suggesting which resources should be turned off. Be specific about "
                        "resource names and potential savings."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content
        
    except ImportError:
        # OpenAI library not installed, fall back to mock
        return _generate_mock_waste_summary(waste_df)
    except Exception as e:
        # API call failed, fall back to mock
        print(f"OpenAI API error: {e}. Using mock response.")
        return _generate_mock_waste_summary(waste_df)


def _build_waste_analysis_prompt(waste_df: pd.DataFrame) -> str:
    """
    Business Logic: Build prompt for OpenAI analysis.
    
    Formats the waste DataFrame into a structured prompt that helps
    the AI understand the context and generate relevant recommendations.
    """
    if len(waste_df) == 0:
        return "No wasteful resources found."
    
    prompt = "Analyze these wasteful cloud resources and suggest which to turn off:\n\n"
    
    for idx, row in waste_df.iterrows():
        prompt += f"Resource: {row.get('service', 'N/A')}\n"
        prompt += f"  - Instance Type: {row.get('instance_type', 'N/A')}\n"
        prompt += f"  - Region: {row.get('region', 'N/A')}\n"
        prompt += f"  - Daily Cost: ${row.get('daily_cost', 0):.2f}\n"
        prompt += f"  - CPU Usage: {row.get('usage_cpu_avg', 'N/A')}\n"
        prompt += f"  - Memory Usage: {row.get('usage_mem_avg', 'N/A')}\n"
        prompt += f"  - Status: {row.get('status', 'N/A')}\n"
        prompt += "\n"
    
    prompt += "\nProvide a concise summary (2-3 sentences) suggesting which resources to turn off and why."
    
    return prompt


def _generate_mock_waste_summary(waste_df: pd.DataFrame) -> str:
    """
    Business Logic: Generate mock waste summary when OpenAI is unavailable.
    
    This ensures the application continues to function in development/testing
    environments without requiring OpenAI API access.
    """
    if len(waste_df) == 0:
        return "No wasteful resources detected. All resources appear to be properly utilized."
    
    total_daily_cost = waste_df['daily_cost'].sum()
    total_monthly_cost = total_daily_cost * 30
    
    summary = f"Waste Detection Summary (Mock Response):\n\n"
    summary += f"Found {len(waste_df)} wasteful resource(s) that should be considered for termination:\n\n"
    
    for idx, row in waste_df.iterrows():
        service = row.get('service', 'Unknown')
        daily_cost = row.get('daily_cost', 0)
        status = row.get('status', 'unknown')
        cpu_usage = row.get('usage_cpu_avg', 'N/A')
        
        summary += f"• {service}: "
        if status.lower() == 'idle':
            summary += f"Status is IDLE - should be terminated immediately. "
        else:
            summary += f"CPU usage is {cpu_usage} (below 5% threshold) - should be terminated or downsized. "
        summary += f"Saves ${daily_cost:.2f}/day (${daily_cost * 30:.2f}/month).\n"
    
    summary += f"\nTotal potential savings: ${total_daily_cost:.2f}/day (${total_monthly_cost:.2f}/month)."
    summary += "\n\nNote: This is a mock response. Set OPENAI_API_KEY for AI-powered analysis."
    
    return summary
