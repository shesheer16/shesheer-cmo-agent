import argparse
import sys
import os
import sqlite3
from pathlib import Path

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
            print_failure("Gemini API key not configured (still 'your_key_here' or empty)")
            return False

        try:
            client = genai.Client(api_key=settings.gemini_api_key)
            # A minimal request to check auth
            response = client.models.generate_content(
                model=settings.default_model,
                contents="test",
                config={"max_output_tokens": 1}
            )
            print_success(f"Gemini API reachable and authenticated using {settings.default_model}")
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
        print_info("Testing sentence-transformers (downloading if necessary)...")
        # Load small model to verify it works
        model = SentenceTransformer('all-MiniLM-L6-v2')
        print_success("sentence-transformers model 'all-MiniLM-L6-v2' is accessible")
        return True
    except ImportError:
        print_failure("sentence-transformers library not installed")
        return False
    except Exception as e:
        print_failure(f"sentence-transformers model check failed: {e}")
        return False

def check_faster_whisper():
    try:
        from src.config import settings
        from faster_whisper import WhisperModel
        print_info(f"Testing faster-whisper model '{settings.whisper_model}' (downloading if necessary)...")
        model = WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")
        print_success(f"faster-whisper model '{settings.whisper_model}' is accessible")
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

def main():
    parser = argparse.ArgumentParser(description="Shesheer CMO Agent")
    parser.add_argument("--health", action="store_true", help="Check all system components are working")
    parser.add_argument("--ingest", action="store_true", help="Run ingestion pipeline (Phase 2)")
    parser.add_argument("--chat", action="store_true", help="Start interactive chat mode (Phase 4)")
    parser.add_argument("--bot", action="store_true", help="Start Telegram bot (Phase 6)")
    parser.add_argument("--ui", action="store_true", help="Start Streamlit UI (Phase 6)")
    
    args = parser.parse_args()

    if args.health:
        run_health_checks()
    elif args.ingest:
        print("Ingestion pipeline will run here (Phase 2).")
    elif args.chat:
        print("Interactive chat mode will start here (Phase 4).")
    elif args.bot:
        print("Telegram bot will start here (Phase 6).")
    elif args.ui:
        print("Streamlit UI will start here (Phase 6).")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
