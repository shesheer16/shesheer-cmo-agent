import sys
import os
import argparse
sys.path.insert(0, os.path.abspath('.'))

from src.memory.context_manager import context_manager
from src.memory.database import SessionLocal
from src.memory.models import StartupContext

def main():
    parser = argparse.ArgumentParser(description="Manage Startup Context for CMO Agent")
    parser.add_argument("--set", type=str, help="Set a context field in format key=value")
    parser.add_argument("--show", action="store_true", help="Show current context summary")
    parser.add_argument("--reset", action="store_true", help="Reset all startup context (Careful!)")
    
    args = parser.parse_args()
    
    if args.set:
        try:
            key, value = args.set.split("=", 1)
            context_manager.update_context(key.strip(), value.strip())
            print(f"Successfully set {key} = {value}")
        except ValueError:
            print("Error: --set argument must be in format key=value")
            
    elif args.show:
        summary = context_manager.get_context_summary()
        print("\n--- CURRENT STARTUP CONTEXT ---")
        print(summary)
        print("-------------------------------\n")
        
    elif args.reset:
        confirm = input("Are you sure you want to delete ALL startup context? (y/N): ")
        if confirm.lower() == 'y':
            db = SessionLocal()
            try:
                db.query(StartupContext).delete()
                db.commit()
                print("Context reset successfully.")
            finally:
                db.close()
        else:
            print("Reset cancelled.")
            
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
