import os
from typing import Optional

class Config:
    """Configuration class for the Voice Cloning App"""
    
    # ElevenLabs API Configuration
    ELEVENLABS_API_KEY: Optional[str] = os.getenv(
        'ELEVENLABS_API_KEY', 
        'sk_41e50eb5f2f1733635044711930a64afcab410374fad0fec'
    )
    
    # Database Configuration
    DATABASE_PATH: str = os.getenv('DATABASE_PATH', 'users.db')
    
    # Security Configuration
    SESSION_EXPIRY_DAYS: int = int(os.getenv('SESSION_EXPIRY_DAYS', '7'))
    MIN_PASSWORD_LENGTH: int = int(os.getenv('MIN_PASSWORD_LENGTH', '6'))
    
    # Audio Configuration
    MAX_AUDIO_FILE_SIZE_MB: int = int(os.getenv('MAX_AUDIO_FILE_SIZE_MB', '10'))
    SUPPORTED_AUDIO_FORMATS: list = ['wav', 'mp3', 'flac', 'm4a']
    DEFAULT_SAMPLE_RATE: int = int(os.getenv('DEFAULT_SAMPLE_RATE', '22050'))
    
    # TTS Configuration
    DEFAULT_STABILITY: float = float(os.getenv('DEFAULT_STABILITY', '0.5'))
    DEFAULT_SIMILARITY_BOOST: float = float(os.getenv('DEFAULT_SIMILARITY_BOOST', '0.5'))
    
    # App Configuration
    APP_TITLE: str = "🎙️ Voice Cloning Application"
    APP_DESCRIPTION: str = "Advanced voice cloning platform with ElevenLabs API integration"
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate configuration settings"""
        if not cls.ELEVENLABS_API_KEY:
            print("Warning: ElevenLabs API key not found")
            return False
        
        if cls.MIN_PASSWORD_LENGTH < 6:
            print("Warning: Minimum password length should be at least 6 characters")
            return False
        
        return True

# Environment file template
ENV_TEMPLATE = """
# ElevenLabs API Configuration
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Database Configuration
DATABASE_PATH=users.db

# Security Configuration
SESSION_EXPIRY_DAYS=7
MIN_PASSWORD_LENGTH=6

# Audio Configuration
MAX_AUDIO_FILE_SIZE_MB=10
DEFAULT_SAMPLE_RATE=22050

# TTS Configuration
DEFAULT_STABILITY=0.5
DEFAULT_SIMILARITY_BOOST=0.5
"""

def create_env_file():
    """Create a .env template file"""
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write(ENV_TEMPLATE)
        print("Created .env template file. Please update with your actual API keys.")

if __name__ == "__main__":
    create_env_file()
    Config.validate_config()
