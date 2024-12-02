from flask import Flask, jsonify
from datetime import datetime
import threading
import logging

logger = logging.getLogger(__name__)

class APIHandler:
    def __init__(self, port=5000):
        self.app = Flask(__name__)
        self.port = port
        self.prompts = []
        self.responses = []
        self.current_memory = ""
        self.setup_routes()
        
    def setup_routes(self):
        @self.app.route('/api/prompts', methods=['GET'])
        def get_prompts():
            return jsonify({
                'prompts': self.prompts,
                'total': len(self.prompts)
            })
            
        @self.app.route('/api/responses', methods=['GET'])
        def get_responses():
            return jsonify({
                'responses': self.responses,
                'total': len(self.responses)
            })
            
        @self.app.route('/api/memory', methods=['GET'])
        def get_memory():
            return jsonify({
                'memory': self.current_memory
            })
    
    def start(self):
        threading.Thread(target=self._run_server, daemon=True).start()
        
    def _run_server(self):
        self.app.run(host='0.0.0.0', port=self.port)
        
    def record_prompt(self, prompt):
        self.prompts.append({
            'timestamp': datetime.now().isoformat(),
            'content': prompt,
            'index': len(self.prompts) + 1
        })
        
    def record_response(self, response, start_time, end_time):
        self.responses.append({
            'start_timestamp': start_time.isoformat(),
            'end_timestamp': end_time.isoformat(),
            'content': response,
            'index': len(self.responses) + 1
        })
        
    def update_memory(self, memory):
        self.current_memory = memory 