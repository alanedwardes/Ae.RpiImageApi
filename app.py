from flask import Flask, request, send_file, jsonify, redirect
import subprocess
import os
import tempfile
import json
import uuid
import sys
from pathlib import Path

app = Flask(__name__)

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

@app.route('/generate', methods=['POST'])
def generate_image():
    print("=== GENERATE ENDPOINT CALLED ===", file=sys.stdout, flush=True)
    try:
        data = request.get_json()
        print(f"Request data: {data}", file=sys.stdout, flush=True)
        
        if not data or 'prompt' not in data:
            return jsonify({'error': 'Missing prompt in request body'}), 400
        
        prompt = data['prompt']
        steps = data.get('steps', 1)
        width = data.get('width', 512)
        height = data.get('height', 512)
        seed = data.get('seed', -1)
        negative_prompt = data.get('negative_prompt', '')
        
        # Create unique output file in configured directory
        unique_id = str(uuid.uuid4())
        output_filename = f"generated_{unique_id}.png"
        output_path = os.path.join(CONFIG['output_dir'], output_filename)
        
        # Build command
        cmd = [
            CONFIG['sd_executable_path'],
            '--turbo',
            '--models-path', CONFIG['models_path'],
            '--prompt', prompt,
            '--steps', str(steps),
            '--seed', str(seed),
            '--res', f"{width}x{height}",
            '--output', output_path
        ]
        
        if negative_prompt:
            cmd.extend(['--neg-prompt', negative_prompt])
        
        command_str = ' '.join(cmd)
        print(f"Running command: {command_str}", file=sys.stdout, flush=True)
        
        # Execute command
        result = subprocess.run(cmd, text=True, timeout=900)
        
        print(f"Command completed with return code: {result.returncode}", file=sys.stdout, flush=True)
        
        if result.returncode != 0:
            return jsonify({
                'error': 'Image generation failed'
            }), 500
        
        # Check if output file exists
        if not os.path.exists(output_path):
            return jsonify({'error': 'Output file not found'}), 500
        
        # Redirect to the generated image
        return redirect(f'/images/{output_filename}')
        
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Image generation timed out'}), 408
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/images/<filename>', methods=['GET'])
def serve_image(filename):
    file_path = os.path.join(CONFIG['output_dir'], filename)
    if os.path.exists(file_path):
        return send_file(file_path, mimetype='image/png')
    else:
        return jsonify({'error': 'Image not found'}), 404

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    load_config()
    app.run(host='0.0.0.0', port=5000, debug=True)
