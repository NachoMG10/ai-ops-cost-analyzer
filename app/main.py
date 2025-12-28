"""
FastAPI main application for AI Ops Cost Analyzer.
"""

import csv
import io
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from app.models import (
    CostRecord,
    CostRecordResponse,
    AnalysisSummary,
    CostSavingsReport,
    CSVUploadResponse
)
from app.analysis import CostAnalyzer
from app.ai_service import AIService
from app.services.analysis import (
    load_csv_to_dataframe,
    detect_waste,
    get_waste_summary,
    generate_openai_waste_summary
)

# Initialize FastAPI app
app = FastAPI(root_path="/cloudsavings-ai", 
    title="AI Ops Cost Analyzer",
    description="AI-powered cloud cost analysis and optimization recommendations",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (in production, use a database)
cost_records_store: List[CostRecord] = []

# Business Logic: Default CSV path for analysis
DEFAULT_CSV_PATH = "dummy_data.csv"

# Initialize services
cost_analyzer = CostAnalyzer()
ai_service = AIService(
    use_mock=not bool(os.getenv("OPENAI_API_KEY")),
    api_key=os.getenv("OPENAI_API_KEY")
)

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint - returns HTML page"""
    html_file = Path(__file__).parent / "templates" / "index.html"
    if html_file.exists():
        with open(html_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    
    # Fallback to JSON if HTML file doesn't exist
    return JSONResponse({
        "message": "AI Ops Cost Analyzer API",
        "version": "1.0.0",
        "endpoints": {
            "upload_csv": "/api/v1/upload-csv",
            "analyze_pandas": "POST /analyze (uses Pandas, detects waste, generates AI summary)",
            "analyze": "GET /api/v1/analyze",
            "generate_report": "/api/v1/generate-report",
            "health": "/health"
        }
    })


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "records_count": len(cost_records_store)}


@app.post("/api/v1/upload-csv", response_model=CSVUploadResponse)
async def upload_csv(file: UploadFile = File(...)):
    """
    Upload and parse CSV file with cost data.
    
    Expected CSV format:
    service,region,instance_type,daily_cost,usage_cpu_avg,usage_mem_avg,date,status
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV file")
    
    try:
        # Read file content
        contents = await file.read()
        text = contents.decode('utf-8')
        
        # Parse CSV
        csv_reader = csv.DictReader(io.StringIO(text))
        records = []
        
        for row in csv_reader:
            try:
                # Parse date
                from datetime import datetime
                date_obj = datetime.strptime(row['date'], '%Y-%m-%d').date()
                
                # Create CostRecord
                record = CostRecord(
                    service=row['service'],
                    region=row['region'],
                    instance_type=row['instance_type'],
                    daily_cost=float(row['daily_cost']),
                    usage_cpu_avg=row['usage_cpu_avg'],
                    usage_mem_avg=row['usage_mem_avg'],
                    date=date_obj,
                    status=row['status'].lower()
                )
                records.append(record)
            except Exception as e:
                # Skip invalid rows but log error
                print(f"Error parsing row: {row}, Error: {e}")
                continue
        
        if not records:
            raise HTTPException(
                status_code=400,
                detail="No valid records found in CSV file"
            )
        
        # Store records (in production, save to database)
        global cost_records_store
        cost_records_store = records
        
        # Perform analysis
        analysis_summary = cost_analyzer.analyze_records(records)
        
        return CSVUploadResponse(
            message=f"Successfully processed {len(records)} records",
            records_processed=len(records),
            analysis_summary=analysis_summary
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing CSV file: {str(e)}"
        )


@app.get("/api/v1/analyze", response_model=AnalysisSummary)
async def analyze_costs():
    """
    Analyze uploaded cost data and return summary.
    Detects underutilized resources, idle resources, and high-cost anomalies.
    """
    if not cost_records_store:
        raise HTTPException(
            status_code=404,
            detail="No cost data available. Please upload a CSV file first."
        )
    
    analysis_summary = cost_analyzer.analyze_records(cost_records_store)
    return analysis_summary


@app.post("/analyze")
async def analyze_with_pandas(
    csv_path: Optional[str] = Query(
        None,
        description="Path to CSV file. If not provided, uses dummy_data.csv"
    )
) -> Dict[str, Any]:
    """
    Business Logic: Core analysis endpoint using Pandas DataFrame.
    
    This endpoint implements the main analysis workflow:
    1. Loads CSV data into a Pandas DataFrame for efficient manipulation
    2. Applies rule-based waste detection (CPU < 5% or status == 'idle')
    3. Generates AI-powered summary using OpenAI (with mock fallback)
    4. Returns comprehensive analysis results
    
    The waste detection rules are based on industry best practices:
    - Resources with status 'idle' are not generating value
    - Resources with CPU < 5% are extremely underutilized
    - Both categories represent opportunities for cost savings
    
    Args:
        csv_path: Optional path to CSV file. Defaults to dummy_data.csv in root.
        
    Returns:
        Dictionary containing:
        - waste_summary: Statistics about detected waste
        - ai_summary: Natural language recommendations from OpenAI
        - waste_dataframe: Detailed data about wasteful resources
    """
    try:
        # Business Logic: Determine CSV file path
        if csv_path is None:
            # Use default dummy_data.csv in project root
            project_root = Path(__file__).parent.parent
            csv_path = str(project_root / DEFAULT_CSV_PATH)
        else:
            # Use provided path
            csv_path = str(Path(csv_path))
        
        # Business Logic: Load CSV into Pandas DataFrame
        # This allows efficient data manipulation and analysis
        if not os.path.exists(csv_path):
            raise HTTPException(
                status_code=404,
                detail=f"CSV file not found: {csv_path}"
            )
        
        df = load_csv_to_dataframe(csv_path)
        
        # Business Logic: Apply waste detection rules
        # Flags resources that are idle or have CPU usage < 5%
        df_with_waste = detect_waste(df)
        
        # Business Logic: Extract wasteful resources for AI analysis
        waste_df = df_with_waste[df_with_waste['is_waste'] == True].copy()
        
        # Business Logic: Generate summary statistics
        waste_summary = get_waste_summary(df_with_waste)
        
        # Business Logic: Generate AI-powered natural language summary
        # Uses OpenAI to analyze waste data and suggest which resources to turn off
        # Falls back to mock response if API key is missing (ensures app doesn't crash)
        ai_summary = generate_openai_waste_summary(
            waste_df,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Prepare response
        response = {
            "waste_summary": waste_summary,
            "ai_summary": ai_summary,
            "waste_count": len(waste_df),
            "total_resources": len(df),
            "waste_resources": waste_df.to_dict('records') if len(waste_df) > 0 else []
        }
        
        return response
        
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"CSV file not found: {csv_path}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error during analysis: {str(e)}"
        )


@app.get("/api/v1/generate-report", response_model=CostSavingsReport)
async def generate_cost_savings_report(
    use_mock: bool = Query(
        False,
        description="Use mock AI service instead of OpenAI (for testing)"
    )
):
    """
    Generate AI-powered cost savings report.
    Uses OpenAI to generate comprehensive recommendations based on cost analysis.
    """
    if not cost_records_store:
        raise HTTPException(
            status_code=404,
            detail="No cost data available. Please upload a CSV file first."
        )
    
    # Perform analysis
    analysis_summary = cost_analyzer.analyze_records(cost_records_store)
    
    # Generate AI report
    if use_mock:
        service = AIService(use_mock=True)
    else:
        service = ai_service
    
    try:
        report = service.generate_cost_savings_report(analysis_summary)
        return report
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating AI report: {str(e)}"
        )


@app.get("/api/v1/records", response_model=List[CostRecordResponse])
async def get_all_records():
    """Get all cost records with analysis flags"""
    if not cost_records_store:
        return []
    
    analysis_summary = cost_analyzer.analyze_records(cost_records_store)
    
    # Build response with all records
    all_responses = []
    for record in cost_records_store:
        is_underutilized = cost_analyzer.is_underutilized(record)
        is_idle = cost_analyzer.is_idle(record)
        avg_cost = sum(r.daily_cost for r in cost_records_store) / len(cost_records_store)
        is_anomaly = cost_analyzer.is_high_cost_anomaly(record, avg_cost)
        
        response = CostRecordResponse.from_cost_record(
            record,
            is_underutilized,
            is_idle,
            is_anomaly
        )
        all_responses.append(response)
    
    return all_responses


@app.get("/api/v1/records/{service_name}", response_model=CostRecordResponse)
async def get_record_by_service(service_name: str):
    """Get cost record for a specific service"""
    if not cost_records_store:
        raise HTTPException(status_code=404, detail="No cost data available")
    
    record = next(
        (r for r in cost_records_store if r.service == service_name),
        None
    )
    
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Service '{service_name}' not found"
        )
    
    is_underutilized = cost_analyzer.is_underutilized(record)
    is_idle = cost_analyzer.is_idle(record)
    avg_cost = sum(r.daily_cost for r in cost_records_store) / len(cost_records_store)
    is_anomaly = cost_analyzer.is_high_cost_anomaly(record, avg_cost)
    
    return CostRecordResponse.from_cost_record(
        record,
        is_underutilized,
        is_idle,
        is_anomaly
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
