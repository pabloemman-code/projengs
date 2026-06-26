# PVP Professor Virtual de Pilotagem

Este é um aplicativo desktop para Windows projetado para analisar suas voltas em simuladores de corrida (como iRacing, Assetto Corsa, F1 24, Automobilista 2, etc.) usando a inteligência artificial do Gemini 2.5.

A aplicação combina um backend em Python (usando `pywebview` para renderizar a janela nativa do Windows e o SDK oficial `google-genai`) com uma interface moderna em HTML/CSS/JS.

## Funcionalidades

- **Seletor de Vídeo Nativo**: Escolha o arquivo de vídeo (.mp4, .mov, etc.) da sua volta direto pelo explorador de arquivos do Windows.
- **Player de Vídeo Integrado**: Assista e controle a reprodução do vídeo da volta diretamente no aplicativo (com suporte a busca rápida de tempo).
- **Templates de Análise (Presets)**:
  - **Treinador Geral**: Relatório completo dividindo a volta por setores/curvas e apontando os 3 pontos críticos de melhora.
  - **Traçado (Racing Line)**: Avalia o uso da largura da pista, pontos de entrada, tangência (apex) e saída.
  - **Frenagem & Aceleração**: Analisa a suavidade da frenagem, trail braking e a retomada de aceleração.
  - **Seleção de Marchas**: Avalia se o motor está na rotação ideal e sugere melhorias nas marchas usadas nas curvas.
- **Instruções Personalizadas**: Adicione contexto sobre seu carro, tração ou pista para refinar a análise da IA.
- **Configurações Seguras**: Salve sua `GEMINI_API_KEY` localmente criptografada utilizando criptografia simétrica Fernet ligada ao usuário do sistema.

## Pré-requisitos

- Windows 10 ou 11 (com WebView2, pré-instalado por padrão no Windows 11 e atualizações do Windows 10).
- Chave de API do Gemini (obtida gratuitamente ou via plano pago no Google AI Studio).

## Como Executar

O projeto foi configurado com o gerenciador de pacotes rápido `uv`, o que significa que você não precisa instalar o Python ou dependências globalmente no seu sistema.

1. Abra o terminal (PowerShell ou Prompt de Comando) na pasta deste projeto:
   `C:\Users\Pablo\.gemini\antigravity\scratch\gemini-lap-analyzer`

2. Execute o comando:
   `uv run main.py`

*Nota: O `uv` fará o download da versão correta do Python em cache e instalará as dependências listadas em `pyproject.toml` automaticamente na primeira execução.*

## Estrutura do Código

- [main.py](file:///C:/Users/Pablo/.gemini/antigravity/scratch/gemini-lap-analyzer/main.py): Código do backend, servidor local de vídeo (Range HTTP Server), gerenciador de configurações e integração com SDK do Gemini.
- [index.html](file:///C:/Users/Pablo/.gemini/antigravity/scratch/gemini-lap-analyzer/index.html): Layout HTML da janela do aplicativo.
- [styles.css](file:///C:/Users/Pablo/.gemini/antigravity/scratch/gemini-lap-analyzer/styles.css): Estilização moderna escura com temática automobilística e animações.
- [app.js](file:///C:/Users/Pablo/.gemini/antigravity/scratch/gemini-lap-analyzer/app.js): Controla a lógica da interface, atualizações de progresso em tempo real e comunicação com o backend em Python.
