import argparse
import sys
import os
import asyncio
import threading
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

def print_success(msg: str):
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")

def print_failure(msg: str):
    print(f"{Colors.RED}✗ {msg}{Colors.RESET}")

def print_info(msg: str):
    print(f"{Colors.CYAN}ℹ {msg}{Colors.RESET}")

def check_env_vars():
    try:
        from src.config import settings
        print_success("All required environment variables present and validated")
        return True
    except Exception as e:
        print_failure(f"Environment variables validation failed: {e}")
        return False

def check_gemini_api():
    try:
        from src.config import settings
        from google import genai
        if settings.gemini_api_key == "your_key_here" or not settings.gemini_api_key:
            print_failure("Gemini API key not configured")
            return False
        try:
            client = genai.Client(api_key=settings.gemini_api_key)
            response = client.models.generate_content(
                model=settings.default_model,
                contents="test",
                config={"max_output_tokens": 1}
            )
            print_success(f"Gemini API reachable using {settings.default_model}")
            return True
        except Exception as e:
            print_failure(f"Gemini API check failed: {e}")
            return False
    except ImportError:
        print_failure("google-genai library not installed")
        return False

def check_chroma_db():
    try:
        from src.config import settings
        db_path = Path(settings.chroma_db_path)
        db_path.mkdir(parents=True, exist_ok=True)
        if os.access(db_path, os.W_OK):
            print_success(f"ChromaDB directory ({db_path}) is present and writable")
            return True
        else:
            print_failure(f"ChromaDB directory ({db_path}) is not writable")
            return False
    except Exception as e:
        print_failure(f"ChromaDB directory check failed: {e}")
        return False

def check_sqlite():
    try:
        from src.config import settings
        db_path = Path(settings.sqlite_db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS _health_check (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()
        print_success(f"SQLite database ({db_path}) is accessible")
        return True
    except Exception as e:
        print_failure(f"SQLite database check failed: {e}")
        return False

def check_sentence_transformers():
    try:
        from sentence_transformers import SentenceTransformer
        print_info("Testing sentence-transformers...")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        print_success("sentence-transformers model accessible")
        return True
    except ImportError:
        print_failure("sentence-transformers library not installed")
        return False
    except Exception as e:
        print_failure(f"sentence-transformers check failed: {e}")
        return False

def check_faster_whisper():
    try:
        from src.config import settings
        from faster_whisper import WhisperModel
        print_info(f"Testing faster-whisper model '{settings.whisper_model}'...")
        model = WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")
        print_success(f"faster-whisper model '{settings.whisper_model}' accessible")
        return True
    except ImportError:
        print_failure("faster-whisper library not installed")
        return False
    except Exception as e:
        print_failure(f"faster-whisper check failed: {e}")
        return False

def run_health_checks():
    print("Running Health Checks for Shesheer CMO Agent...\n")
    checks = [
        check_env_vars,
        check_sqlite,
        check_chroma_db,
        check_sentence_transformers,
        check_faster_whisper,
        check_gemini_api
    ]
    all_passed = True
    for check in checks:
        if not check():
            all_passed = False
    print("\nHealth Check Summary:")
    if all_passed:
        print_success("ALL SYSTEMS OPERATIONAL")
        sys.exit(0)
    else:
        print_failure("SOME CHECKS FAILED. PLEASE FIX ERRORS ABOVE.")
        sys.exit(1)


def start_health_server(port: int):
    """Runs FastAPI/uvicorn in a background daemon thread."""
    import uvicorn
    from src.api.main import app
    port = int(os.environ.get("PORT", 10000))  # ← Use PORT env var
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning")
    server = uvicorn.Server(config)
    server.run()


def start_bot():
    """Starts the Telegram bot in polling mode."""
    
    print_info("DEBUG: start_bot() called")
    
    # Check TELEGRAM_BOT_TOKEN
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not telegram_token or telegram_token == "your_token_here":
        print_failure("TELEGRAM_BOT_TOKEN not set or invalid! Bot cannot start.")
        return
    print_success(f"TELEGRAM_BOT_TOKEN found (length: {len(telegram_token)})")

    # Check GEMINI_API_KEY
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        print_failure("GEMINI_API_KEY not set! Bot cannot start.")
        return
    print_success(f"GEMINI_API_KEY found (length: {len(gemini_key)})")

    # Optional Sentry
    sentry_dsn = os.environ.get("SENTRY_DSN")
    if sentry_dsn:
        try:
            import sentry_sdk
            sentry_sdk.init(dsn=sentry_dsn, traces_sample_rate=0.1)
            print_info("Sentry error tracking active.")
        except ImportError:
            print_info("sentry-sdk not installed — skipping Sentry.")

    # Auto-ingest all sources on cold start
    # DISABLED: We now pre-build the DB and commit it to GitHub for instant startups
    # try:
    #     print_info("Running cold-start ingestion...")
    #     
    #     # 1. Ingest PDFs
    #     from scripts.ingest_pdf_batch import run_batch as ingest_pdfs
    #     ingest_pdfs()
    #     
    #     # 2. Ingest YouTube sources
    #     from scripts.ingest_youtube_batch import run_batch as ingest_youtube
    #     ingest_youtube()
    #     
    #     print_success("Knowledge base ready.")
    # except Exception as e:
    #     print_info(f"Cold-start ingestion skipped: {e}")

    # Start the Telegram bot
    try:
        print_info("DEBUG: Importing telegram_bot...")
        from src.interface.telegram_bot import main as bot_main
        print_success("Telegram bot starting in polling mode...")
        bot_main()
    except Exception as e:
        print_failure(f"Telegram bot failed to start: {e}")
        import traceback
        traceback.print_exc()

def main():
    parser = argparse.ArgumentParser(description="Shesheer CMO Agent")
    parser.add_argument("--health", action="store_true", help="Run system health checks")
    parser.add_argument("--ingest", action="store_true", help="Run ingestion pipeline")
    parser.add_argument("--chat", action="store_true", help="Interactive chat mode")
    parser.add_argument("--bot", action="store_true", help="Start Telegram bot + health server")
    parser.add_argument("--ui", action="store_true", help="Start Streamlit UI")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 10000)),
                        help="Port for the health API server")

    args = parser.parse_args()

    if args.health:
        run_health_checks()

    elif args.ingest:
        print_info("Starting ingestion pipeline...")
        from scripts.ingest_pdf_batch import run_batch
        run_batch()

    elif args.chat:
        print_info("Starting interactive chat...")

        from src.core.orchestrator import CMOAgent
        agent = CMOAgent()
        async def chat_loop():
            while True:
                try:
                    q = input("\nYou: ").strip()
                    if q.lower() in ("exit", "quit"):
                        break
                    response = await agent.respond(q)
                    print(f"\nCMO Agent:\n{response.response_text}")
                except KeyboardInterrupt:
                    break
        asyncio.run(chat_loop())

    elif args.bot:
        # ── Dual process: health server in thread + bot in main ──
        print_info(f"Starting health server on port {args.port}...")
        health_thread = threading.Thread(
            target=start_health_server,
            args=(args.port,),
            daemon=True  # Dies cleanly when bot exits
        )
        health_thread.start()
        print_success(f"Health server running at http://0.0.0.0:{args.port}/health")

        # Bot runs in main thread's event loop
        start_bot()

    elif args.ui:
        print_info("Launch Streamlit UI with: uv run streamlit run streamlit_app.py")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
