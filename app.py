from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
import subprocess
import os
import tempfile
import json
import uuid
import sys
from pathlib import Path
from typing import Optional

app = FastAPI()

# Configuration
CONFIG = {
    'sd_executable_path': '',
    'models_path': '',
    'output_dir': tempfile.gettempdir()
}

def load_config():
    config_file = Path('config.json')
    if config_file.exists():
        with open(config_file, 'r') as f:
            CONFIG.update(json.load(f))

class GenerateRequest(BaseModel):
    prompt: str
    steps: Optional[int] = 1
    width: Optional[int] = 512
    height: Optional[int] = 512
    seed: Optional[int] = -1
    negative_prompt: Optional[str] = ''

@app.post("/generate")
async def generate_image(request: GenerateRequest):
    print("=== GENERATE ENDPOINT CALLED ===")
    print(f"Request data: {request}")
    
    try:
        # Create unique output file in configured directory
        unique_id = str(uuid.uuid4())
        output_filename = f"generated_{unique_id}.png"
        output_path = os.path.join(CONFIG['output_dir'], output_filename)
        
        # Build command
        cmd = [
            CONFIG['sd_executable_path'],
            '--turbo',
            '--models-path', CONFIG['models_path'],
            '--prompt', request.prompt,
            '--steps', str(request.steps),
            '--seed', str(request.seed),
            '--res', f"{request.width}x{request.height}",
            '--output', output_path
        ]
        
        if request.negative_prompt:
            cmd.extend(['--neg-prompt', request.negative_prompt])
        
        command_str = ' '.join(cmd)
        print(f"Running command: {command_str}")
        
        # Execute command
        result = subprocess.run(cmd, text=True, timeout=900)
        
        print(f"Command completed with return code: {result.returncode}")
        
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail="Image generation failed")
        
        # Check if output file exists
        if not os.path.exists(output_path):
            raise HTTPException(status_code=500, detail="Output file not found")
        
        # Redirect to the generated image
        return RedirectResponse(url=f"/images/{output_filename}")
        
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Image generation timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/images/{filename}")
async def serve_image(filename: str):
    file_path = os.path.join(CONFIG['output_dir'], filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="image/png")
    else:
        raise HTTPException(status_code=404, detail="Image not found")

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    load_config()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
