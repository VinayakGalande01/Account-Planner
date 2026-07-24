"""
OPENAPI SPEC EXPORTER (export_openapi.py)
Utility script that extracts the active FastAPI OpenAPI schema JSON object
and writes it directly to the local documentation directory.
"""

# --- SECTION 1: Dependencies & Import Setup ---
# Imports file system utilities, JSON writers, and the FastAPI application object.
import os
import json
from main import app

# --- SECTION 2: Schema Export Routine ---
# Resolves target documentation folders and dumps schema to openapi.json.
def export_spec():
    # Generate the OpenAPI schema dictionary
    openapi_schema = app.openapi()
    
    # Target directory path
    target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "documentation", "API_Architecture"))
    os.makedirs(target_dir, exist_ok=True)
    
    # Save as JSON spec
    json_path = os.path.join(target_dir, "openapi.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)
        
    print(f"[SUCCESS] Exported current OpenAPI schema to {json_path}")
    print("You can copy this JSON to any editor (Swagger UI, ReDoc) to view or generate visual diagrams.")

if __name__ == "__main__":
    export_spec()
