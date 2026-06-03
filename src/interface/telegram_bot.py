import os
import asyncio
import tempfile
import subprocess
from pathlib import Path
from telegram import Update, File
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from faster_whisper import WhisperModel
import google.api_core.exceptions as google_exceptions

from src.core.orchestrator import CMOAgent
from src.memory.context_manager import context_manager
from src.utils.logger import logger
# Assuming we moved run_batch to pdf_processor.py or we just import the script directly.
# Let's import the script's run_batch and wrap it.
from scripts.ingest_pdf_batch import run_batch as ingest_pdf_batch

TELEGRAM_ALLOWED_USER_ID = os.getenv("TELEGRAM_ALLOWED_USER_ID")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

agent = CMOAgent()

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
                
    except google_exceptions.ResourceExhausted:
        await update.message.reply_text("API limit hit, retry in 30 seconds")
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


def main():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_ALLOWED_USER_ID:
        logger.error("Missing Telegram environment variables.")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("context", context_cmd))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    application.add_handler(MessageHandler(filters.VOICE, voice_handler))
    application.add_handler(MessageHandler(filters.Document.PDF, document_handler))

    logger.info("Telegram Bot started.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
