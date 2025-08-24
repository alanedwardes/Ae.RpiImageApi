from flask import Flask, request, send_file, jsonify
import subprocess
import os
import tempfile
import json
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
    try:
        data = request.get_json()
        
        if not data or 'prompt' not in data:
            return jsonify({'error': 'Missing prompt in request body'}), 400
        
        prompt = data['prompt']
        steps = data.get('steps', 1)
        cfg_scale = data.get('cfg_scale', 7.0)
        width = data.get('width', 512)
        height = data.get('height', 512)
        seed = data.get('seed', -1)
        negative_prompt = data.get('negative_prompt', '')
        
        # Create temporary output file
        output_filename = f"generated_{os.getpid()}_{hash(prompt) % 10000}.png"
        output_path = os.path.join(CONFIG['output_dir'], output_filename)
        
        # Build command
        cmd = [
            CONFIG['sd_executable_path'],
            '--turbo',
            '--models-path', CONFIG['models_path'],
            '--prompt', prompt,
            '--steps', str(steps),
            '--cfg-scale', str(cfg_scale),
            '--width', str(width),
            '--height', str(height),
            '--seed', str(seed),
            '--output', output_path
        ]
        
        if negative_prompt:
            cmd.extend(['--negative-prompt', negative_prompt])
        
        # Execute command
        result = subprocess.run(cmd, text=True, timeout=900)
        
        if result.returncode != 0:
            return jsonify({
                'error': 'Image generation failed'
            }), 500
        
        # Check if output file exists
        if not os.path.exists(output_path):
            return jsonify({'error': 'Output file not found'}), 500
        
        # Return the generated image
        return send_file(output_path, mimetype='image/png')
        
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Image generation timed out'}), 408
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    load_config()
    app.run(host='0.0.0.0', port=5000, debug=False)
