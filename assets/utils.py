from dataclasses import dataclass


@dataclass
class Video:
    media: bytes
    duration: int
    width: int
    height: int


@dataclass
class AttachmentParts:
    album_sendings: list
    videos: list
    docs: list
    animations: list
