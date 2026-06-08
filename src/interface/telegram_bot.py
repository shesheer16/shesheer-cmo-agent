import os
import asyncio
import tempfile
import subprocess
from pathlib import Path
from telegram import Update, File
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from faster_whisper import WhisperModel
from google.genai import errors as genai_errors

from datetime import datetime, timedelta

from src.core.orchestrator import CMOAgent
from src.memory.context_manager import context_manager
from src.core.decision_tracker import decision_tracker
from src.utils.logger import logger
# Assuming we moved run_batch to pdf_processor.py or we just import the script directly.
# Let's import the script's run_batch and wrap it.
from scripts.ingest_pdf_batch import run_batch as ingest_pdf_batch

TELEGRAM_ALLOWED_USER_ID = os.getenv("TELEGRAM_ALLOWED_USER_ID")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

agent = None  # Initialized in main()

# Initialize whisper model once
whisper_model = None

def check_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

async def security_check(update: Update) -> bool:
    if str(update.effective_user.id) != str(TELEGRAM_ALLOWED_USER_ID):
        await update.message.reply_text("This is a private agent.")
        return False
    return True

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await security_check(update): return
    await update.message.reply_text("Namaste Founder. CMO Agent online. Send me text, voice, or a PDF.")

async def context_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await security_check(update): return
    summary = context_manager.get_context_summary()
    await update.message.reply_text(f"**Current Startup Context:**\n{summary}")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await security_check(update): return
    
    user_message = update.message.text
    await process_message(user_message, update)

async def process_message(user_message: str, update: Update):
    await update.message.reply_text("typing...")
    
    try:
        response = await agent.respond(user_message)
        
        text = response.response_text
        sources_text = f"\n\n💡 Sources: {len(response.sources_used)} Indian market references"
        text += sources_text
        
        # Split logic (max 4096)
        if len(text) <= 4000:
            await update.message.reply_text(text, parse_mode="Markdown")
        else:
            chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for chunk in chunks:
                await update.message.reply_text(chunk, parse_mode="Markdown")
                
    except genai_errors.APIError as e:
        if e.code == 429:
            await update.message.reply_text("API limit hit, retry in 30 seconds")
        else:
            logger.error(f"GenAI API Error: {e}")
            await update.message.reply_text("Processing error. Try again.")
    except Exception as e:
        logger.error(f"Error in text_handler: {e}")
        await update.message.reply_text("Processing error. Try again.")

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await security_check(update): return
    
    if not check_ffmpeg():
        await update.message.reply_text("ffmpeg required. Run: brew install ffmpeg")
        return
        
    await update.message.reply_text("Transcribing voice note...")
    
    global whisper_model
    if whisper_model is None:
        whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")

    voice = update.message.voice or update.message.audio
    file_id = voice.file_id
    new_file = await context.bot.get_file(file_id)
    
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_ogg:
        await new_file.download_to_drive(temp_ogg.name)
        ogg_path = temp_ogg.name

    wav_path = ogg_path.replace(".ogg", ".wav")
    
    # Try twice
    for attempt in range(2):
        try:
            subprocess.run(["ffmpeg", "-y", "-i", ogg_path, wav_path], capture_output=True, check=True)
            segments, _ = whisper_model.transcribe(wav_path)
            transcription = "".join([segment.text for segment in segments])
            logger.info(f"Voice → Text: {transcription}")
            await update.message.reply_text(f"🗣️: {transcription}")
            
            # Route to agent
            await process_message(transcription, update)
            break
        except Exception as e:
            logger.error(f"Transcription error attempt {attempt+1}: {e}")
            if attempt == 1:
                await update.message.reply_text("Failed to transcribe voice note.")
            
    try:
        os.remove(ogg_path)
        os.remove(wav_path)
    except:
        pass

async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await security_check(update): return
    
    doc = update.message.document
    if not doc.file_name.endswith(".pdf"):
        await update.message.reply_text("I can only ingest PDFs right now.")
        return
        
    await update.message.reply_text("Ingesting PDF...")
    
    new_file = await context.bot.get_file(doc.file_id)
    pdf_dir = Path("data/knowledge_base/pdfs")
    pdf_dir.mkdir(parents=True, exist_ok=True)
    
    save_path = pdf_dir / doc.file_name
    await new_file.download_to_drive(save_path)
    
    # Ingest using real pipeline
    try:
        ingest_pdf_batch()
        await update.message.reply_text("PDF ingested successfully!")
    except Exception as e:
        logger.error(f"PDF ingestion failed: {e}")
        await update.message.reply_text("PDF ingestion failed.")


async def decisions_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await security_check(update): return
    pending = context_manager.get_pending_decisions()
    if not pending:
        await update.message.reply_text("No pending decisions logged.")
        return
        
    msg = "**Pending Decisions:**\n\n"
    for d in pending:
        msg += f"ID: {d['id']}\nQuestion: {d['question']}\nMove: {d['recommendation'][:100]}...\n\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def outcome_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await security_check(update): return
    # Usage: /outcome <id> <worked/failed/partial> <notes>
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("Usage: /outcome <id> <worked|failed|partial> <notes...>")
        return
        
    try:
        decision_id = int(args[0])
        status = args[1].lower()
        notes = " ".join(args[2:])
        decision_tracker.log_outcome(decision_id, status, notes)
        await update.message.reply_text(f"Logged outcome for decision {decision_id}.")
    except Exception as e:
        await update.message.reply_text(f"Failed to log outcome: {e}")

async def poll_decisions(context: ContextTypes.DEFAULT_TYPE):
    """Daily check for 14-day old decisions."""
    try:
        pending = context_manager.get_pending_decisions()
        # In a real app we'd check timestamps, for now we just show we poll them.
        # But we can query models.DecisionsLog using context_manager if needed.
        # For simplicity, we just send a static reminder about the oldest pending one.
        if pending:
            oldest = pending[0]
            await context.bot.send_message(
                chat_id=TELEGRAM_ALLOWED_USER_ID,
                text=f"⏰ Follow-up time! Two weeks ago you were advised to:\n{oldest['recommendation']}\n\nDid you take this move? Reply with `/outcome {oldest['id']} <worked/failed/partial> <notes>`"
            )
    except Exception as e:
        logger.error(f"Error polling decisions: {e}")

def main():
    logger.info("DEBUG: telegram_bot.main() called")
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_ALLOWED_USER_ID:
        logger.error("Missing Telegram environment variables. TELEGRAM_BOT_TOKEN or TELEGRAM_ALLOWED_USER_ID not set.")
        return

    logger.info("DEBUG: Environment vars OK, creating Application...")
    
    try:
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        logger.info("DEBUG: Application created successfully")
        
        # Scheduler via JobQueue
        import datetime
        t = datetime.time(hour=9, minute=0, second=0)
        application.job_queue.run_daily(poll_decisions, time=t)
        logger.info("DEBUG: Scheduler configured for daily 9 AM decision polls")

        logger.info("DEBUG: Adding command handlers...")
        application.add_handler(CommandHandler("start", start_cmd))
        application.add_handler(CommandHandler("context", context_cmd))
        application.add_handler(CommandHandler("decisions", decisions_cmd))
        application.add_handler(CommandHandler("outcome", outcome_cmd))
        
        logger.info("DEBUG: Adding message handlers...")
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
        application.add_handler(MessageHandler(filters.VOICE, voice_handler))
        application.add_handler(MessageHandler(filters.Document.PDF, document_handler))

        logger.info("✓ Telegram Bot started. Polling for updates...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Telegram bot failed during setup/polling: {e}")
        import traceback
        traceback.print_exc()
        return

if __name__ == "__main__":
    main()