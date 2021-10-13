from .utils import output
from .utils import logging
from .utils import metadata
from .utils.source import Source
import os
import shutil
import threading
from typing import List, Dict, Any


class DownloadThread(threading.Thread):
    """Thread for downloading a file"""

    def __init__(self, session, path, url, metadata, progress, task):
        threading.Thread.__init__(self)
        self.session = session
        self.path = path
        self.metadata = metadata
        self.task = task
        self.progress = progress
        self.req = self.session.get(url, stream=True)
        self.length = int(self.req.headers['Content-length'])

    def run(self):
        with open(self.path, "wb") as f:
            for chunk in self.req.iter_content(chunk_size=1024):
                f.write(chunk)
                self.progress.update(self.task, advance=1024)
        if "title" in self.metadata:
            metadata.add_metadata(self.path, {"title": self.metadata["title"]})

    def get_length(self):
        return self.length


def download(source: Source,
             combine: bool = False,
             output_template: str = "{title}",
             output_format: str = "mp3"):
    """Downloads audiobook from source object"""
    # Downloading audiobok info
    source.before()
    source.title = source.get_title()
    files = source.get_files()
    meta = source.get_metadata()
    output_dir = output.gen_output_location(
            output_template,
            source.title,
            meta)
    # Downloading audio files
    filenames = source.download_files(files, output_dir)
    # Single audiofile
    if combine or len(filenames) == 1:
        combined_audiobook(source, filenames, output_dir, output_format, meta)
    # Multiple audiofiles
    else:
        add_metadata_to_dir(source, filenames, output_dir, meta)


def combined_audiobook(source: Source,
                       filenames: List[str],
                       output_dir: str,
                       output_format: str,
                       meta: Dict[Any, Any]):
    """Combines audiobook into a single audio file and embeds metadata"""
    output_file = f"{output_dir}.{output_format}"
    if len(filenames) > 1:
        combine_files(source, filenames, output_dir, output_file)
    embed_metadata_in_file(source, meta, output_file)
    shutil.rmtree(output_dir)


def combine_files(source: Source,
                  filenames: List[str],
                  output_dir: str,
                  output_file: str):
    """Combines audiobook files and cleanes up afterward"""
    logging.log("Combining files")
    output.combine_audiofiles(filenames, output_dir, output_file)
    if not os.path.exists(output_file):
        logging.error("Could not combine audio files")
        exit()


def embed_metadata_in_file(source: Source,
                           meta: Dict[Any, Any],
                           output_file: str):
    """Embed metadata into combined audiobook file"""
    if meta is not None:
        metadata.add_metadata(output_file, meta)
    cover = source.get_cover()
    if cover is not None:
        logging.log("Embedding cover")
        metadata.embed_cover(output_file, cover)
    chapters = source.get_chapters()
    if chapters is not None:
        logging.log("Adding chapters")
        metadata.add_chapters(output_file, chapters)


def add_metadata_to_dir(source: Source,
                        filenames: List[str],
                        output_dir: str,
                        meta: Dict[Any, Any]):
    """Adds metadata to dir of audiobook files"""
    for i in filenames:
        metadata.add_metadata(os.path.join(output_dir, i), meta)
    cover = source.get_cover()
    if cover is not None:
        logging.log("Downloading cover")
        cover_path = os.path.join(
            output_dir,
            f"cover.{source.get_cover_filetype()}")
        with open(cover_path, 'wb') as f:
            f.write(cover)
