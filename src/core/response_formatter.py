import re
from typing import List

class ResponseFormatter:
    
    @staticmethod
    def format_for_telegram(response: str) -> str:
        """
        Converts markdown bold **text** to Telegram bold *text*.
        """
        # Convert markdown bold **text** to Telegram bold *text*
        telegram_text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', response)
        return telegram_text

    @staticmethod
    def format_for_streamlit(response: str) -> str:
        """
        Keeps standard markdown but adds horizontal rules between the 5 memo sections.
        """
        # Add horizontal rule before major headers, except the very first one
        # Assuming headers are like **SITUATION ANALYSIS**
        lines = response.split('\n')
        formatted_lines = []
        
        is_first_header = True
        for line in lines:
            if line.startswith('**') and line.endswith('**') and line.isupper():
                if not is_first_header:
                    formatted_lines.append("\n---\n")
                is_first_header = False
            formatted_lines.append(line)
            
        return '\n'.join(formatted_lines)

    @staticmethod
    def format_for_voice(response: str) -> str:
        """
        Removes markdown symbols, converts bold headers to natural speech transitions,
        and removes source citations for text-to-speech engine consumption.
        """
        voice_text = response
        
        # Remove source citations like [1] or [Source: x]
        voice_text = re.sub(r'\[\d+\]', '', voice_text)
        voice_text = re.sub(r'\(Source:.*?\)', '', voice_text)
        
        # Convert specific headers to natural speech transitions
        transitions = {
            "**SITUATION ANALYSIS**": "First, looking at the situation.",
            "**INDIAN MARKET PRECEDENT**": "Here is the Indian market precedent.",
            "**THE MOVE**": "Here is the specific move you should make.",
            "**THE TRAP TO AVOID**": "Now, here is the trap to avoid.",
            "**THE QUESTION YOU HAVEN'T ASKED**": "Finally, the question you haven't asked."
        }
        
        for header, transition in transitions.items():
            voice_text = voice_text.replace(header, transition)
            
        # Remove remaining markdown bold/italic
        voice_text = voice_text.replace('**', '')
        voice_text = voice_text.replace('*', '')
        
        # Clean up multiple newlines or spaces
        voice_text = re.sub(r'\n+', '. ', voice_text)
        voice_text = re.sub(r'\s+', ' ', voice_text)
        
        return voice_text.strip()

response_formatter = ResponseFormatter()
