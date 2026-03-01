"""File storage helpers for project assets."""
import os
from pathlib import Path

STORAGE_DIR = Path(os.environ.get("STORAGE_DIR", "./storage/projects"))


def project_dir(project_id: str) -> Path:
    d = STORAGE_DIR / project_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def scenes_dir(project_id: str) -> Path:
    d = project_dir(project_id) / "scenes"
    d.mkdir(parents=True, exist_ok=True)
    return d


def overlays_dir(project_id: str) -> Path:
    d = project_dir(project_id) / "overlays"
    d.mkdir(parents=True, exist_ok=True)
    return d


def final_path(project_id: str) -> Path:
    return project_dir(project_id) / "final.mp4"


def voiceover_path(project_id: str) -> Path:
    return project_dir(project_id) / "voiceover.mp3"


def character_path(project_id: str) -> Path:
    return project_dir(project_id) / "character.png"


def scene_path(project_id: str, idx: int) -> Path:
    return scenes_dir(project_id) / f"scene_{idx:02d}.mp4"
