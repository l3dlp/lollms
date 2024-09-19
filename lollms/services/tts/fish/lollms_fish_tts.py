from pathlib import Path
from typing import List, Dict, Any
import httpx
from pydantic import BaseModel
from lollms.app import LollmsApplication
from lollms.paths import LollmsPaths
from lollms.tts import LollmsTTS
from lollms.utilities import PackageManager, find_next_available_filename

if not PackageManager.check_package_installed("sounddevice"):
    PackageManager.install_package("sounddevice")
if not PackageManager.check_package_installed("soundfile"):
    PackageManager.install_package("soundfile")

if not PackageManager.check_package_installed("ormsgpack"):
    PackageManager.install_package("ormsgpack")

import ormsgpack

import sounddevice as sd
import soundfile as sf

class ServeReferenceAudio(BaseModel):
    audio: bytes
    text: str

class ServeTTSRequest(BaseModel):
    text: str
    chunk_length: int = 200
    format: str = "mp3"
    mp3_bitrate: int = 128
    references: List[ServeReferenceAudio] = []
    reference_id: str | None = None
    normalize: bool = True
    latency: str = "normal"

def get_FishAudioTTS(lollms_paths: LollmsPaths):
    return LollmsFishAudioTTS

class LollmsFishAudioTTS(LollmsTTS):
    def __init__(
        self,
        app: LollmsApplication,
        voice_name: str = "default",
        api_key: str = "",
        output_path: Path | str = None,
        reference_folder: Path | str = None
    ):
        super().__init__("fishaudio_tts", app, "default", voice_name, api_key, output_path)
        self.reference_folder = Path(reference_folder) if reference_folder else None
        self.voices = self._load_voices()
        self.ready = True

    def _load_voices(self) -> List[str]:
        if not self.reference_folder or not self.reference_folder.exists():
            return ["default"]
        
        voices = []
        for audio_file in self.reference_folder.glob("*.mp3"):
            text_file = audio_file.with_suffix(".txt")
            if text_file.exists():
                voices.append(audio_file.stem)
        return voices or ["default"]

    def set_voice(self, voice_name: str):
        if voice_name in self.voices:
            self.voice_name = voice_name
        else:
            raise ValueError(f"Voice '{voice_name}' not found. Available voices: {', '.join(self.voices)}")

    def _get_reference_audio(self, voice_name: str) -> ServeReferenceAudio | None:
        if voice_name == "default":
            return None
        
        audio_file = self.reference_folder / f"{voice_name}.mp3"
        text_file = self.reference_folder / f"{voice_name}.txt"
        
        if audio_file.exists() and text_file.exists():
            return ServeReferenceAudio(
                audio=audio_file.read_bytes(),
                text=text_file.read_text()
            )
        return None

    def tts_file(self, text, file_name_or_path: Path | str = None, speaker=None, language="en", use_threading=False):
        speech_file_path = Path(file_name_or_path) if file_name_or_path else self._get_output_path("mp3")
        
        reference = self._get_reference_audio(speaker)
        request = ServeTTSRequest(
            text=text,
            references=[reference] if reference else []
        )

        with httpx.Client() as client:
            with client.stream(
                "POST",
                "https://api.fish.audio/v1/tts",
                content=ormsgpack.packb(request, option=ormsgpack.OPT_SERIALIZE_PYDANTIC),
                headers={
                    "authorization": f"Bearer {self.api_key}",
                    "content-type": "application/msgpack",
                },
                timeout=None,
            ) as response:
                with open(speech_file_path, "wb") as f:
                    for chunk in response.iter_bytes():
                        f.write(chunk)

        return speech_file_path

    def tts_audio(self, text, speaker: str = None, file_name_or_path: Path | str = None, language="en", use_threading=False):
        speech_file_path = self.tts_file(text, file_name_or_path, speaker, language, use_threading)
        
        def play_audio(file_path):
            data, fs = sf.read(file_path, dtype='float32')
            sd.play(data, fs)
            sd.wait()

        play_audio(speech_file_path)

    def _get_output_path(self, extension: str) -> Path:
        if self.output_path:
            return find_next_available_filename(self.output_path, f"output.{extension}")
        return find_next_available_filename(Path.cwd(), f"output.{extension}")