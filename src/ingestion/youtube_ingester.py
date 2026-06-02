import os
import re
import json
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from faster_whisper import WhisperModel
from tenacity import retry, wait_exponential, stop_after_attempt

from src.utils.logger import logger

YOUTUBE_DATA_DIR = Path("data/knowledge_base/youtube")
YOUTUBE_DATA_DIR.mkdir(parents=True, exist_ok=True)

class YouTubeIngester:
    def __init__(self):
        self.whisper_model = None

    def _get_whisper_model(self):
        if self.whisper_model is None:
            logger.info("Loading faster-whisper 'base' model...")
            self.whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
        return self.whisper_model

    def _extract_video_id(self, url_or_id: str) -> str:
        # Extracts 11 char video id
        match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url_or_id)
        if match:
            return match.group(1)
        return url_or_id 

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _fetch_metadata(self, url: str) -> dict:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                return info
            except Exception as e:
                if "Private video" in str(e) or "private" in str(e).lower():
                    logger.error(f"Video is private: {url}")
                    raise ValueError(f"Private video: {url}")
                logger.warning(f"Error fetching metadata, retrying... ({e})")
                raise

    def _clean_text(self, text: str) -> str:
        # Removes [Music], (Applause), and standardizes whitespace
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'\(.*?\)', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _get_api_transcript(self, video_id: str) -> Optional[List[Dict[str, Any]]]:
        try:
            # Try English and Hindi
            api = YouTubeTranscriptApi()
            transcript_list = api.list(video_id)
            transcript = transcript_list.find_transcript(['en', 'hi', 'en-IN'])
            return transcript.fetch()
        except (TranscriptsDisabled, NoTranscriptFound, Exception) as e:
            logger.info(f"Auto-captions unavailable via API for {video_id}. Reason: {e}")
            return None

    def _transcribe_with_whisper(self, url: str) -> List[Dict[str, Any]]:
        logger.info(f"Downloading audio for Whisper transcription: {url}")
        with tempfile.TemporaryDirectory() as tmpdir:
            outtmpl = os.path.join(tmpdir, "audio.%(ext)s")
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': outtmpl,
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}],
                'quiet': True,
                'no_warnings': True
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except Exception as e:
                logger.error(f"Failed to download audio for {url}: {e}")
                raise RuntimeError(f"Audio download failed: {e}")
            
            audio_files = list(Path(tmpdir).glob("audio.*"))
            if not audio_files:
                raise RuntimeError("Audio file not found after yt-dlp download.")
            
            audio_path = str(audio_files[0])
            model = self._get_whisper_model()
            
            logger.info("Transcribing audio with faster-whisper...")
            segments, _ = model.transcribe(audio_path, beam_size=5)
            
            transcript = []
            for segment in segments:
                transcript.append({
                    "text": segment.text,
                    "start": segment.start,
                    "duration": segment.end - segment.start
                })
            return transcript

    def _segment_transcript(self, raw_transcript: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        segments = []
        current_segment_text = []
        current_segment_start = None
        current_word_count = 0
        last_end_time = 0.0

        for item in raw_transcript:
            if isinstance(item, dict):
                start_time = item.get('start', 0.0)
                duration = item.get('duration', 0.0)
                text = self._clean_text(item.get('text', ''))
            else:
                start_time = getattr(item, 'start', 0.0)
                duration = getattr(item, 'duration', 0.0)
                text = self._clean_text(getattr(item, 'text', ''))
            
            if not text:
                continue

            words = text.split()
            word_count = len(words)
            end_time = start_time + duration

            if current_segment_start is None:
                current_segment_start = start_time

            # Segment if gap > 3 seconds, or we hit 2000 words
            time_gap = start_time - last_end_time
            if (time_gap > 3.0 and current_segment_text) or (current_word_count + word_count) > 2000:
                segments.append({
                    "start_time": current_segment_start,
                    "text": " ".join(current_segment_text),
                    "word_count": current_word_count
                })
                current_segment_text = [text]
                current_segment_start = start_time
                current_word_count = word_count
            else:
                current_segment_text.append(text)
                current_word_count += word_count
            
            last_end_time = end_time

        if current_segment_text:
            segments.append({
                "start_time": current_segment_start,
                "text": " ".join(current_segment_text),
                "word_count": current_word_count
            })

        return segments

    def process_video(self, url_or_id: str) -> Optional[Dict[str, Any]]:
        video_id = self._extract_video_id(url_or_id)
        url = f"https://www.youtube.com/watch?v={video_id}"

        try:
            logger.info(f"Processing YouTube video: {video_id}")
            # 5. Extracts metadata
            meta = self._fetch_metadata(url)
            title = meta.get("title", "")
            channel = meta.get("uploader", "")
            date = meta.get("upload_date", "")
            description = meta.get("description", "")
            if description:
                description = description[:500]
            duration = meta.get("duration", 0)

            # 2 & 3. Transcript API or Whisper fallback
            method = "api"
            raw_transcript = self._get_api_transcript(video_id)
            
            if not raw_transcript:
                method = "whisper"
                raw_transcript = self._transcribe_with_whisper(url)

            if not raw_transcript:
                logger.error(f"Failed to extract any transcript for {video_id}")
                return None

            # 9. Logs
            logger.info(f"Video {video_id} processed. Method: {method}. Duration: {duration}s")

            # 4 & 6. Cleans transcript and splits into segments
            segments = self._segment_transcript(raw_transcript)

            # 7. Returns structured dict
            result = {
                "video_id": video_id,
                "title": title,
                "channel": channel,
                "date": date,
                "description": description,
                "transcript_method": method,
                "segments": segments
            }

            # 8. Saves raw transcript to data/knowledge_base/youtube/
            save_path = YOUTUBE_DATA_DIR / f"{video_id}.json"
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved processed transcript to {save_path}")

            return result
            
        except ValueError as ve:
            logger.error(str(ve))
            return None
        except Exception as e:
            logger.error(f"Failed to process video {video_id}: {e}")
            return None

if __name__ == "__main__":
    # Test execution
    ingester = YouTubeIngester()
    ingester.process_video("jNQXAC9IVRw") # "Me at the zoo"
