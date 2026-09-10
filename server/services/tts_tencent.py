"""TTS service using Tencent Cloud TTS API."""

import os
import logging
from pathlib import Path

from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.tts.v20190823 import tts_client, models

logger = logging.getLogger("peppa.tts_tencent")

# Tencent Cloud credentials from environment variables
TENCENT_SECRET_ID = os.environ.get("TENCENT_SECRET_ID", "")
TENCENT_SECRET_KEY = os.environ.get("TENCENT_SECRET_KEY", "")

# Available English voice types (child-friendly)
# 601001: English female (standard)
# 601002: English male (standard)
# 601003: English child (cute, recommended for kids)
# 101001: English male (older API)
# 101002: English female (older API)
DEFAULT_VOICE_TYPE = 601003  # Child voice


def generate_tts_tencent(text: str, output_path: str, voice_type: int = DEFAULT_VOICE_TYPE, speed: int = 0) -> str:
    """Generate TTS audio using Tencent Cloud TTS API.
    
    Args:
        text: English text to synthesize.
        output_path: Where to save the mp3 file.
        voice_type: Voice type ID. Default is 601003 (English child).
        speed: Speed adjustment (-10 to 10), 0 is normal.
    
    Returns:
        Path to the generated audio file.
    """
    if not TENCENT_SECRET_ID or not TENCENT_SECRET_KEY:
        raise RuntimeError("TENCENT_SECRET_ID and TENCENT_SECRET_KEY environment variables are required")
    
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Create credential
        cred = credential.Credential(TENCENT_SECRET_ID, TENCENT_SECRET_KEY)
        
        # Setup client profile
        httpProfile = HttpProfile()
        httpProfile.endpoint = "tts.tencentcloudapi.com"
        httpProfile.reqMethod = "POST"
        
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        
        # Create client
        client = tts_client.TtsClient(cred, "ap-guangzhou", clientProfile)
        
        # Create request
        import uuid
        req = models.TextToVoiceRequest()
        req.Text = text
        req.VoiceType = voice_type
        req.Speed = speed
        req.SampleRate = 24000
        req.SessionId = str(uuid.uuid4())
        
        # Call API
        resp = client.TextToVoice(req)
        
        # Decode base64 audio data
        import base64
        audio_data = base64.b64decode(resp.Audio)
        
        # Save to file
        output.write_bytes(audio_data)
        
        logger.info("Tencent TTS generated: %s -> %s (voice=%d)", text[:30], output_path, voice_type)
        return str(output)
        
    except Exception as e:
        logger.error("Tencent TTS failed: %s", str(e))
        raise


def check_tencent_tts_available() -> bool:
    """Check if Tencent TTS credentials are available."""
    return bool(TENCENT_SECRET_ID and TENCENT_SECRET_KEY)
