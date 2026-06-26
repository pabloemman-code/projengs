// Wait for DOM to load
document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const apiKeyInput = document.getElementById("api-key");
    const toggleApiKeyBtn = document.getElementById("toggle-api-key");
    const modelSelect = document.getElementById("model-select");
    const saveSettingsBtn = document.getElementById("save-settings-btn");
    
    const presetButtons = document.querySelectorAll(".preset-btn");
    const customPromptTextarea = document.getElementById("custom-prompt");
    
    const selectVideoBtn = document.getElementById("select-video-btn");
    const changeVideoBtn = document.getElementById("change-video-btn");
    const videoPlaceholder = document.getElementById("video-placeholder");
    const videoWrapper = document.getElementById("video-wrapper");
    const videoPlayer = document.getElementById("video-player");
    const videoFilename = document.getElementById("video-filename");
    
    const analyzeBtn = document.getElementById("analyze-btn");
    const statusCard = document.getElementById("status-card");
    const statusTitle = document.getElementById("status-title");
    const statusMessage = document.getElementById("status-message");
    const statusProgress = document.getElementById("status-progress");
    
    const analysisWelcome = document.getElementById("analysis-welcome");
    const analysisResult = document.getElementById("analysis-result");
    
    const toast = document.getElementById("toast");
    const toastIcon = document.getElementById("toast-icon");
    const toastMessage = document.getElementById("toast-message");

    let selectedPreset = "general";
    let isVideoSelected = false;

    // Initialize - load saved settings when API becomes ready
    window.addEventListener("pywebviewready", () => {
        loadSettings();
    });

    // -------------------------------------------------------------------------
    // Event Listeners
    // -------------------------------------------------------------------------
    
    // Toggle password visibility
    toggleApiKeyBtn.addEventListener("click", () => {
        const type = apiKeyInput.getAttribute("type") === "password" ? "text" : "password";
        apiKeyInput.setAttribute("type", type);
        const icon = toggleApiKeyBtn.querySelector("i");
        icon.className = type === "password" ? "fa-solid fa-eye" : "fa-solid fa-eye-slash";
    });

    // Save settings button
    saveSettingsBtn.addEventListener("click", () => {
        const key = apiKeyInput.value.trim();
        const model = modelSelect.value;
        
        if (!key) {
            showToast("A chave de API não pode estar em branco.", "error");
            return;
        }

        window.pywebview.api.save_settings(key, model).then((res) => {
            if (res.success) {
                showToast("Configurações salvas com sucesso!", "success");
            } else {
                showToast("Erro ao salvar configurações.", "error");
            }
        }).catch(err => {
            showToast("Erro na ponte de API: " + err, "error");
        });
    });

    // Preset selection
    presetButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            presetButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            selectedPreset = btn.getAttribute("data-preset");
        });
    });

    // Select Video Button
    selectVideoBtn.addEventListener("click", triggerVideoSelection);
    changeVideoBtn.addEventListener("click", triggerVideoSelection);

    function triggerVideoSelection() {
        window.pywebview.api.select_video().then((res) => {
            if (res.success) {
                isVideoSelected = true;
                videoFilename.innerHTML = `<i class="fa-solid fa-file-video"></i> ${res.name}`;
                
                // Show player, hide placeholder
                videoPlaceholder.classList.add("hidden");
                videoWrapper.classList.remove("hidden");
                
                // Load video source
                videoPlayer.src = res.url;
                videoPlayer.load();
                
                // Enable analysis button
                analyzeBtn.disabled = false;
                
                // Reset analysis states
                analysisWelcome.classList.remove("hidden");
                analysisResult.classList.add("hidden");
                statusCard.classList.add("hidden");
                
                showToast("Vídeo carregado com sucesso!", "success");
            }
        }).catch(err => {
            showToast("Erro ao abrir seletor de arquivos: " + err, "error");
        });
    }

    // Start Analysis Button
    analyzeBtn.addEventListener("click", () => {
        if (!isVideoSelected) return;

        const customPrompt = customPromptTextarea.value.trim();
        
        // UI States
        analyzeBtn.disabled = true;
        analysisWelcome.classList.add("hidden");
        analysisResult.classList.add("hidden");
        statusCard.classList.remove("hidden");
        
        // Initial progress state
        updateProgress("uploading", "Enviando arquivo de vídeo para a IA...");

        window.pywebview.api.analyze_video(selectedPreset, customPrompt).then((res) => {
            if (!res.success) {
                showError(res.error);
                analyzeBtn.disabled = false;
            }
        }).catch(err => {
            showError("Falha ao iniciar processo de análise: " + err);
            analyzeBtn.disabled = false;
        });
    });

    // -------------------------------------------------------------------------
    // Python Callbacks (Bound to Window Global Scope)
    // -------------------------------------------------------------------------
    
    // Update progress state
    window.updateProgress = (stage, message) => {
        statusMessage.textContent = message;
        
        if (stage === "uploading") {
            statusTitle.textContent = "Passo 1/3: Carregando Vídeo";
            statusProgress.style.width = "20%";
        } else if (stage === "processing") {
            statusTitle.textContent = "Passo 2/3: Processando na Nuvem";
            statusProgress.style.width = "50%";
        } else if (stage === "analyzing") {
            statusTitle.textContent = "Passo 3/3: Analisando Pilotagem";
            statusProgress.style.width = "85%";
        }
    };

    // Render results
    window.displayAnalysis = (markdownText) => {
        statusCard.classList.add("hidden");
        analysisResult.classList.remove("hidden");
        
        // Parse markdown beautifully
        analysisResult.innerHTML = parseMarkdown(markdownText);
        
        // Reset buttons
        analyzeBtn.disabled = false;
        showToast("Análise concluída com sucesso!", "success");
    };

    // Show error state
    window.showError = (errorMessage) => {
        statusCard.classList.add("hidden");
        analysisWelcome.classList.remove("hidden");
        analyzeBtn.disabled = false;
        
        showToast(errorMessage, "error");
    };

    // -------------------------------------------------------------------------
    // Helper Functions
    // -------------------------------------------------------------------------
    
    function loadSettings() {
        window.pywebview.api.get_settings().then((settings) => {
            if (settings.api_key) {
                apiKeyInput.value = settings.api_key;
            }
            if (settings.model) {
                modelSelect.value = settings.model;
            }
        }).catch(err => {
            console.error("Failed to load settings:", err);
        });
    }

    function showToast(message, type = "info") {
        toastMessage.textContent = message;
        toast.className = "toast"; // Reset classes
        
        if (type === "error") {
            toast.classList.add("error");
            toastIcon.className = "fa-solid fa-triangle-exclamation";
        } else if (type === "success") {
            toast.classList.add("success");
            toastIcon.className = "fa-solid fa-circle-check";
            // Set green styling locally in JS as a fallback if class override is needed
            toast.style.borderColor = "var(--accent-secondary)";
            toastIcon.style.color = "var(--accent-secondary)";
        } else {
            toastIcon.className = "fa-solid fa-info-circle";
            toast.style.borderColor = "var(--accent)";
            toastIcon.style.color = "var(--accent)";
        }
        
        toast.classList.remove("hidden");
        
        // Auto-hide toast after 4 seconds
        clearTimeout(window.toastTimeout);
        window.toastTimeout = setTimeout(() => {
            toast.classList.add("hidden");
        }, 4000);
    }

    // Markdown Parser Fallback
    function parseMarkdown(text) {
        // Try marked.js first
        if (window.marked && typeof window.marked.parse === 'function') {
            return window.marked.parse(text);
        }
        
        // Very basic custom fallback regex parser for offline/failsafe
        console.warn("Marked library not found. Falling back to basic regex parser.");
        
        let html = text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
        
        // Heading 3
        html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
        // Heading 2
        html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
        // Heading 1
        html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
        
        // Bold
        html = html.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
        
        // Inline code/highlights
        html = html.replace(/`(.*?)`/gim, '<code>$1</code>');
        
        // Blockquotes
        html = html.replace(/^\>\s+(.*$)/gim, '<blockquote>$1</blockquote>');
        
        // Unordered List Items
        html = html.replace(/^\s*-\s+(.*$)/gim, '<li>$1</li>');
        html = html.replace(/^\s*\*\s+(.*$)/gim, '<li>$1</li>');
        
        // Paragraphs / line endings
        html = html.split('\n').map(line => {
            line = line.trim();
            if (!line) return '<br>';
            if (line.startsWith('<h') || line.startsWith('<li') || line.startsWith('<block') || line.startsWith('<ul') || line.startsWith('</ul')) {
                return line;
            }
            return `<p>${line}</p>`;
        }).join('\n');
        
        // Wrap contiguous list items in <ul> tags
        // This is a naive regex grouping for lists
        html = html.replace(/(<li>.*<\/li>)/gims, '<ul>$1</ul>');
        
        return html;
    }
});
