from flask import Flask, jsonify
from flask_sock import Sock
from datetime import datetime
import threading
import logging

logger = logging.getLogger(__name__)

class APIHandler:
    def __init__(self, port=5000):
        self.app = Flask(__name__)
        self.sock = Sock(self.app)
        self.port = port
        self.prompts = []
        self.responses = []
        self.current_memory = ""
        self.model_handler = None
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
            
        @self.sock.route('/ws')
        def ws_handler(ws):
            while True:
                try:
                    ws.receive()
                except:
                    break
                    
    def set_model_handler(self, model_handler):
        self.model_handler = model_handler
        
    def broadcast_ws_message(self, message: str):
        if hasattr(self, '_ws_clients'):
            for ws in self._ws_clients:
                try:
                    ws.send(message)
                except:
                    continue
        
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