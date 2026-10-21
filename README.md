# ⚡ BNF DOCS 2.0 - Sistema Inteligente de Emissão de Declarações & Bot Telegram

Sistema corporativo de alta precisão para preenchimento, edição e emissão de declarações oficiais em formato PDF, com integração completa ao **Telegram Bot** (Webhook Serverless + Polling) e **Painel de Controle Super-Admin** moderno em tempo real com tema dark glassmorphism e ícones 100% vetoriais SVG.

Repositório Oficial: [https://github.com/JamesSilva7K/bnfbotforce.git](https://github.com/JamesSilva7K/bnfbotforce.git)

---

## 🌟 Destaques & Principais Funcionalidades

### 1. 🤖 Bot do Telegram Inteligente & Ultrarrápido (Serverless + Polling)
* **Reconhecimento Avançado de Contas:** Identifica automaticamente os operadores pelo Telegram, capturando e sincronizando:
  * **Avatar oficial** em alta resolução diretamente da API do Telegram.
  * **Nome completo** e **@username**.
  * **Data do primeiro contato** e **registro de última atividade**.
* **Fluxo Guiado Simplificado (3 Etapas):**
  1. **Nome Completo do Lead** (em caixa alta e negrito).
  2. **RG** (com pontuação e formatação automática: `379467471` ➔ `37.946.747-1`).
  3. **CPF** (com pontuação e barra automática: `34009182881` ➔ `340.091.828/81`).
* **Revisão Imediata e Confirmação por Botões:** Resumo executivo com botões interativos para alteração rápida de campos e botão direto de emissão oficial.
* **Importação Rápida Inteligente (NLP):** Envie os dados em uma única mensagem e o sistema detecta, pontua e gera o documento.

---

### 2. 📄 Edição PDF Cirúrgica & Fiel (`pdf_engine.py`)
* **Alteração Estrita:** Altera exclusivamente o **Nome do Lead**, **RG** e **CPF**, preservando 100% dos carimbos, assinaturas, marcas d'água e dados institucionais da entidade matriz (**ACSICA**).
* **Fontes Oficiais Bundled:** Inclui arquivos TrueType oficiais de `Arial` e `Arial Bold` (`storage/fonts/`), garantindo renderização vetorial idêntica em qualquer ambiente (Windows, Linux, Docker, Vercel).
* **Pontuação Automática:** Reconhece números crus ou pontuados e aplica o padrão exato da declaração modelo sem quebras de layout.

---

### 3. 👑 Painel Super-Admin com Design de Alto Padrão (`app.py`)
* **100% Ícones Vetoriais SVG:** Todos os emojis literais foram substituídos por ícones vetoriais modernos com suporte a gradientes e temas HSL.
* **Perfil do Administrador no Menu Lateral:** Rodapé com o avatar oficial do Telegram, nome real (**NG7Kz**) e @handle (**@NG7Ks**).
* **Gestão e Controle de Acesso:** Visualize a lista de administradores com fotos reais, dados de contato e botões de 1 clique para revogar ou reativar permissões em tempo real.
* **Auditoria Completa & Download Seguro:** Registro de cada documento emitido com hash de integridade criptográfica SHA-256 e download direto do PDF gerado.

---

## ☁️ Como Hospedar Gratuitamente na Vercel (Host Free)

O sistema foi preparado para rodar perfeitamente no ambiente serverless gratuito da **Vercel** com suporte a **Webhook do Telegram** para respostas instantâneas:

### Passo 1: Importar no GitHub e Vercel
1. Conecte o repositório `https://github.com/JamesSilva7K/bnfbotforce.git` à sua conta da [Vercel](https://vercel.com).
2. Na tela de importação do projeto, mantenha as configurações padrão (o arquivo `vercel.json` cuidará de todo o roteamento do Python WSGI automaticamente).
3. Adicione as Variáveis de Ambiente opcionais se desejar:
   * `TELEGRAM_BOT_TOKEN`: Token do seu bot obtido no `@BotFather`.
   * `SUPER_ADMIN_USER`: Usuário do painel (padrão: `admin`).
   * `SUPER_ADMIN_PASS`: Senha do painel (padrão: `admin1234`).
   * `SECRET_KEY`: Chave de segurança para sessões Flask.
4. Clique em **Deploy**.

### Passo 2: Ativar o Webhook do Telegram
Assim que o deploy for concluído:
1. Acesse o seu painel web publicado (ex: `https://seu-projeto.vercel.app`).
2. Faça login com suas credenciais.
3. Acesse o menu **Configurações & Bot** (`/settings`).
4. Clique no botão **Ativar Webhook Vercel**.
5. O sistema enviará a URL do webhook (`/api/telegram-webhook`) diretamente para a API do Telegram. A partir desse momento, todas as mensagens do bot serão respondidas instantaneamente via serverless!

---

## 💻 Execução Local / Servidor Dedicado (Polling)

Se preferir rodar em uma VPS ou localmente na máquina:

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Iniciar sistema completo (Dashboard + Bot Polling)
python run_system.py
```

* **Dashboard Web:** [http://127.0.0.1:5000](http://127.0.0.1:5000)
* **Usuário:** `admin` | **Senha:** `admin1234`

---

## 📁 Estrutura do Repositório

```
bnfbotforce/
├── api/
│   └── index.py              # Entrypoint serverless para o runtime da Vercel
├── vercel.json               # Configurações de rotas e build da Vercel
├── requirements.txt          # Dependências Python para Vercel e produção
├── config.py                 # Gerenciamento de diretórios e variáveis de ambiente
├── database.py               # Banco de dados SQLite com WAL mode e auditoria
├── pdf_engine.py             # Engine de renderização vetorial de PDF com PyMuPDF
├── bot.py                    # Bot inteligente do Telegram (Webhook & Polling)
├── app.py                    # Painel Web Flask Super-Admin com controle de acesso
├── run_system.py             # Orquestrador concorrente para execução local/VPS
├── Documentos/
│   └── declaração tuzinho.pdf# Template oficial matriz da ACSICA
├── storage/
│   ├── fonts/                # Fontes Arial e Arial Bold bundled
│   ├── avatars/              # Armazenamento de avatares sincronizados do Telegram
│   └── system.db             # Base de dados SQLite local
├── static/
│   └── css/
│       └── dashboard.css     # Design system em Vanilla CSS com glassmorphism
└── templates/                # Telas em HTML5 com ícones vetoriais SVG
    ├── base.html
    ├── login.html
    ├── dashboard.html
    ├── admins.html
    ├── documents.html
    ├── document_detail.html
    ├── generate.html
    └── settings.html
```

---

Desenvolvido para máxima precisão, conformidade visual e velocidade operacional.
