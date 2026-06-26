import sys
import os
import json
import base64
import re
import mimetypes
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import webview
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from google import genai
from google.genai import types

# -----------------------------------------------------------------------------
# Configuration Manager
# -----------------------------------------------------------------------------
class ConfigManager:
    def __init__(self, filename="config.json"):
        self.filename = filename
        self.salt = b'racing-gemini-salt-123'
        self.key = self._generate_key()
        self.fernet = Fernet(self.key)
        
    def _generate_key(self):
        try:
            username = os.getlogin()
        except Exception:
            username = "default_user"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(username.encode()))
        return key
        
    def save_settings(self, api_key, model="gemini-2.5-flash"):
        encrypted_key = self.fernet.encrypt(api_key.encode()).decode()
        data = {
            "api_key": encrypted_key,
            "model": model
        }
        try:
            with open(self.filename, "w") as f:
                json.dump(data, f)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
            
    def load_settings(self):
        if not os.path.exists(self.filename):
            return {"api_key": "", "model": "gemini-2.5-flash"}
        try:
            with open(self.filename, "r") as f:
                data = json.load(f)
            encrypted_key = data.get("api_key", "")
            model = data.get("model", "gemini-2.5-flash")
            
            if not encrypted_key:
                return {"api_key": "", "model": model}
                
            decrypted_key = self.fernet.decrypt(encrypted_key.encode()).decode()
            return {"api_key": decrypted_key, "model": model}
        except Exception as e:
            print(f"Error loading config: {e}")
            return {"api_key": "", "model": "gemini-2.5-flash"}

# -----------------------------------------------------------------------------
# Range Request HTTP Server (to stream local videos to WebView2 player)
# -----------------------------------------------------------------------------
class RangeRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # Suppress command line log cluttering
        
    def do_GET(self):
        video_path = getattr(self.server, 'video_path', None)
        if not video_path or not os.path.exists(video_path):
            self.send_error(404, "File not found")
            return
            
        file_size = os.path.getsize(video_path)
        mime_type, _ = mimetypes.guess_type(video_path)
        if not mime_type:
            mime_type = 'application/octet-stream'
            
        range_header = self.headers.get('Range')
        
        if range_header:
            match = re.match(r'bytes=(\d+)-(\d*)', range_header)
            if match:
                start = int(match.group(1))
                end = match.group(2)
                end = int(end) if end else file_size - 1
                
                if start >= file_size or end >= file_size or start > end:
                    self.send_response(416)
                    self.send_header('Content-Range', f'bytes */{file_size}')
                    self.end_headers()
                    return
                    
                self.send_response(206)
                self.send_header('Content-Type', mime_type)
                self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
                self.send_header('Content-Length', str(end - start + 1))
                self.send_header('Accept-Ranges', 'bytes')
                self.end_headers()
                
                try:
                    with open(video_path, 'rb') as f:
                        f.seek(start)
                        bytes_to_read = end - start + 1
                        chunk_size = 64 * 1024
                        while bytes_to_read > 0:
                            read_size = min(chunk_size, bytes_to_read)
                            data = f.read(read_size)
                            if not data:
                                break
                            self.wfile.write(data)
                            bytes_to_read -= len(data)
                except (ConnectionAbortedError, ConnectionResetError, OSError):
                    pass # normal when scrubbing video
                return
                
        self.send_response(200)
        self.send_header('Content-Type', mime_type)
        self.send_header('Content-Length', str(file_size))
        self.send_header('Accept-Ranges', 'bytes')
        self.end_headers()
        
        try:
            with open(video_path, 'rb') as f:
                chunk_size = 64 * 1024
                while True:
                    data = f.read(chunk_size)
                    if not data:
                        break
                    self.wfile.write(data)
        except (ConnectionAbortedError, ConnectionResetError, OSError):
            pass

# -----------------------------------------------------------------------------
# WebView JS Bridge API
# -----------------------------------------------------------------------------
class ApiBridge:
    def __init__(self, config_mgr, server_port, webview_window):
        self.config_mgr = config_mgr
        self.server_port = server_port
        self.window = webview_window
        self.selected_video = None
        
    def select_video(self):
        file_types = ('Video Files (*.mp4;*.mov;*.avi;*.mkv)', 'All files (*.*)')
        result = self.window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=file_types
        )
        if result:
            self.selected_video = result[0]
            # Bind selected video to local HTTP server
            self.window.server.video_path = self.selected_video
            return {
                "success": True,
                "path": self.selected_video,
                "name": os.path.basename(self.selected_video),
                "url": f"http://127.0.0.1:{self.server_port}/video"
            }
        return {"success": False}
        
    def get_settings(self):
        settings = self.config_mgr.load_settings()
        return settings
        
    def save_settings(self, api_key, model):
        success = self.config_mgr.save_settings(api_key, model)
        return {"success": success}
        
    def analyze_video(self, preset, custom_prompt):
        if not self.selected_video:
            return {"success": False, "error": "Nenhum arquivo de vídeo selecionado."}
            
        settings = self.config_mgr.load_settings()
        api_key = settings.get("api_key", "")
        model = settings.get("model", "gemini-2.5-flash")
        
        if not api_key:
            return {"success": False, "error": "Chave de API do Gemini não configurada nas configurações."}
            
        # Run the analysis in a background thread to prevent UI freezing
        thread = threading.Thread(target=self._run_gemini_analysis, args=(api_key, model, preset, custom_prompt))
        thread.daemon = True
        thread.start()
        return {"success": True, "message": "Análise iniciada no servidor."}
        
    def _run_gemini_analysis(self, api_key, model, preset, custom_prompt):
        def update_ui_status(stage, msg):
            # JS script to run
            js_code = f"window.updateProgress('{stage}', `{msg.replace('`','\\`').replace('${','\\${')}`)"
            self.window.evaluate_js(js_code)
            
        try:
            update_ui_status("uploading", "Enviando arquivo de vídeo para a IA...")
            
            client = genai.Client(api_key=api_key)
            
            # 1. Upload video file to File API
            video_file = client.files.upload(file=self.selected_video)
            
            # 2. Wait for processing (Gemini requires video processing first)
            update_ui_status("processing", "IA processando o vídeo (isso pode levar de 1 a 3 minutos)...")
            
            start_time = time.time()
            while True:
                video_file = client.files.get(name=video_file.name)
                state = video_file.state.name
                if state == "ACTIVE":
                    break
                elif state == "FAILED":
                    raise ValueError("Falha no processamento do vídeo no servidor da IA.")
                
                # Check timeout (e.g. 5 minutes)
                if time.time() - start_time > 300:
                    raise TimeoutError("O processamento do vídeo expirou.")
                    
                time.sleep(3)
                
            # 3. Formulate the prompt
            presets = {
                "racing_line": (
                    "Analise detalhadamente o traçado (racing line) do carro ao longo da pista neste vídeo de simulador. "
                    "Identifique se o piloto está usando toda a largura da pista na entrada, tangência (apex) e saída das curvas. "
                    "Aponte curvas específicas onde o piloto poderia entrar mais aberto, tangenciar melhor ou usar melhor a zebra de saída."
                ),
                "braking_throttle": (
                    "Analise os pontos de frenagem e aplicação do acelerador neste vídeo de simulador. "
                    "Avalie se o piloto está freando no momento certo ou muito cedo/tarde, se está fazendo trail braking (aliviando o freio progressivamente enquanto entra na curva) "
                    "e se a aplicação de aceleração na saída é feita de forma suave e rápida."
                ),
                "gears": (
                    "Analise a seleção de marchas do piloto ao longo da volta neste vídeo de simulador. "
                    "Indique se o motor está na faixa correta de rotação ou se curvas específicas poderiam ser feitas em uma marcha mais alta (para estabilizar o carro) "
                    "ou mais baixa (para conseguir melhor tração e torque na saída)."
                ),
                "general": (
                    "Você é um engenheiro de pista profissional e treinador de pilotagem. Analise esta volta completa do simulador. "
                    "Forneça um relatório estruturado avaliando o desempenho do piloto. Identifique os 3 pontos críticos de melhora "
                    "e dê orientações práticas de pilotagem para que ele consiga baixar o tempo de volta."
                )
            }
            
            prompt = presets.get(preset, presets["general"])
            if custom_prompt:
                prompt += f"\n\nInstruções adicionais fornecidas pelo usuário:\n{custom_prompt}"
                
            prompt += (
                "\n\nResponda em PORTUGUÊS (Brasil). "
                "Use formatação Markdown estruturada (com títulos, tópicos e negrito) para facilitar a leitura."
            )
            
            # 4. Generate Analysis
            update_ui_status("analyzing", "Analisando pilotagem e gerando feedback técnico...")
            
            response = client.models.generate_content(
                model=model,
                contents=[video_file, prompt]
            )
            
            # Clean up uploaded video in background
            try:
                client.files.delete(name=video_file.name)
            except Exception as e:
                print(f"Error deleting file: {e}")
                
            # Send result back to Frontend
            js_result = f"window.displayAnalysis(`{response.text.replace('`','\\`').replace('${','\\${')}`)"
            self.window.evaluate_js(js_result)
            
        except Exception as e:
            err_msg = str(e)
            js_error = f"window.showError(`{err_msg.replace('`','\\`').replace('${','\\${')}`)"
            self.window.evaluate_js(js_error)

# -----------------------------------------------------------------------------
# Main Application Launcher
# -----------------------------------------------------------------------------
def main():
    config_mgr = ConfigManager()
    
    # 1. Start Range request server on random free port
    server = HTTPServer(('127.0.0.1', 0), RangeRequestHandler)
    server.video_path = None
    server_port = server.server_port
    
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    # Resolve assets path for PyInstaller package
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        assets_dir = sys._MEIPASS
    else:
        assets_dir = os.path.dirname(os.path.abspath(__file__))
        
    index_path = os.path.join(assets_dir, "index.html")

    # 2. Setup Bridge and WebView Window
    # Create the bridge instance (window will be attached after window creation)
    bridge = ApiBridge(config_mgr, server_port, None)

    # Setup WebView Window with js_api parameter for exposing class instance bridge
    window = webview.create_window(
        title="PVP - Professor Virtual de Pilotagem",
        url=index_path,
        width=1200,
        height=800,
        min_size=(900, 600),
        resizable=True,
        js_api=bridge
    )
    
    # Expose custom server reference to the window
    window.server = server
    
    # Attach window reference back to bridge
    bridge.window = window
    
    # 4. Run pywebview
    # On Windows, WebView2 will load index.html from local files automatically
    webview.start(debug=True)

if __name__ == "__main__":
    main()
