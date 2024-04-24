#!/usr/bin/env python
import ffmpeg
import click
import os
import logging
import yaml
from datetime import datetime
import colorlog
from enum import Enum


SUPPORTED_GOLF_CLUBS = [
    # wedges
    "L", "S","G", "A", "P", 
    # irons
    "9", "8", "7", "6", "5", "4", "3", "2", "1", 
    # woods
    "7W", "5W", "4W", "3W", 
    # hybrids
    "5H", "4H", "3H",
    # driver
    "D"]
CONFIG_DIRECTORY_NAME="golfhelper"
CONFIG_FILE_NAME="config.yaml"
CONFIG_KEYS = Enum('ConfigKey', ['ROOT', 'MAX_VIDEO_SIZE_MB'])

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler  = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = colorlog.ColoredFormatter(
    '[%(log_color)s%(levelname)s]: %(message)s',
    log_colors={
        'DEBUG':    'cyan',
        'INFO':     'green',
        'WARNING':  'yellow',
        'ERROR':    'red',
        'CRITICAL': 'red,bg_white',
    }
)
handler.setFormatter(formatter)
logger.addHandler(handler)

init = click.Group(help='Helper for organizing golf swing videos')

@init.command('setup_tool', help='Sets up the root directory to save golf videos')
@click.option('--root', prompt='Root directory to use', help='Root directory for golf videos', type=click.Path(exists=False, file_okay=False, dir_okay=True, writable=True))
@click.option('--max-video-size-mb', default=5)
def setup_tool(root, max_video_size_mb):
    """
    Creates a config file with where the root directory should be stored.
    """
    if root.startswith('~'):
        root = os.path.expanduser(root)
    config_dir = get_config_dir()
    if not os.path.exists(config_dir):
        logger.info("Config not found. Creating directory at: {}".format(config_dir))
        os.makedirs(config_dir)
    with open(os.path.join(config_dir, CONFIG_FILE_NAME), 'w') as config:
        logger.info("Configuring golf helper root directory to: {}".format(root))
        data = {
            CONFIG_KEYS.ROOT.name: root,
            CONFIG_KEYS.MAX_VIDEO_SIZE_MB.name: max_video_size_mb
        }
        os.makedirs(root, exist_ok=True)
        yaml.dump(data, config, default_flow_style=False)
    logger.info("Finished setup!")


@init.command('organize', help='Organizes a video into its proper folder')
@click.option('--video', prompt='Video to organize', help='Video to convert and organize')
@click.option('--club', prompt='Club used in video', help='Club used in the video', type=click.Choice(SUPPORTED_GOLF_CLUBS, case_sensitive=False))
def organize(video, club):
    """
    1. Load our config to check where videos should be stored
    2. Create directory for our new videos along with directory for analysis
    3. Convert video to mp4 format
    4. Compress video if necessary
    """
    # Load our config to check where videos should be stored
    if video.startswith('~'):
        video = os.path.expanduser(video)
    original_path = video
    config = get_config()
    root_dir = config[CONFIG_KEYS.ROOT.name]
    max_video_size_bytes = config[CONFIG_KEYS.MAX_VIDEO_SIZE_MB.name] * 1024 * 1024

    if not video.lower().endswith('.mov') and not video.lower().endswith('.mp4'):
        logger.error("Video provided is not a supported format.")
        return
    # Create directory for our new videos along with directory for analysis
    date = datetime.now().strftime('%y-%m-%d')
    new_golf_dir = os.path.join(root_dir, date)
    golf_video_dir = os.path.join(new_golf_dir, 'videos')
    golf_analysis_dir = os.path.join(new_golf_dir, 'analyze')
    os.makedirs(new_golf_dir, exist_ok=True)
    os.makedirs(golf_video_dir, exist_ok=True)
    os.makedirs(golf_analysis_dir, exist_ok=True)

    counter = 0
    output_file=os.path.join(golf_video_dir, club + "_" + str(counter))
    output_file_compressed = os.path.join(output_file + ".mp4")
    output_file_uncompressed = os.path.join(output_file + "_unc" + ".mp4")
    while os.path.exists(output_file_compressed):
        counter += 1
        output_file=os.path.join(golf_video_dir, club + "_" + str(counter))
        output_file_compressed = os.path.join(output_file + ".mp4")
        output_file_uncompressed = os.path.join(output_file + "_unc" + ".mp4")

    # Convert video to mp4 format
    if video.lower().endswith('.mov'):
        logger.info("Converting video from mov to mp4...")
        ffmpeg_convert_cmd = (
            ffmpeg
                .input(video)
                .output(output_file_uncompressed, **{'c:v': 'copy', 'c:a': 'copy'})
                .overwrite_output()
                .run_async(pipe_stdout=True, pipe_stderr=True)
        )
        print_ffmpeg(ffmpeg_convert_cmd)
        video = output_file_uncompressed
        ffmpeg_convert_cmd.wait()

    # Compress video if necessary
    video_size = os.path.getsize(video)
    if video_size > max_video_size_bytes:
        logger.info("Compressing video...")
        ffmpeg_compress_cmd = (
            ffmpeg
                .input(video)
                .output(output_file_compressed, vf='scale=iw/2:-1', strict='-2')
                .overwrite_output()
                .run_async(pipe_stdout=True, pipe_stderr=True)
        )
        print_ffmpeg(ffmpeg_compress_cmd)
        ffmpeg_compress_cmd.wait()
    else:
        os.rename(video, output_file_compressed)
    if os.path.exists(output_file_uncompressed):
        logger.info("Removing uncompressed video...")
        os.remove(output_file_uncompressed)
    logger.info("Created a video at: {}".format(output_file_compressed))
    response = click.prompt("Delete the original video? (y/n)", type=click.Choice(['y','n','Y', 'N']))
    if response.lower() == 'y':
        os.remove(original_path)

def print_ffmpeg(cmd):
    for line in cmd.stdout:
        logger.debug(line.decode().strip())
    for line in cmd.stderr:
        logger.debug(line.decode().strip())

def get_config_dir():
    if os.name == 'posix':
        return os.path.expanduser("~/.config/" + CONFIG_DIRECTORY_NAME)
    elif os.name == 'nt':
        return os.path.join(os.getenv('APPDATA'), CONFIG_DIRECTORY_NAME)
    else: 
        raise OSError("Unsupported operating system")

def get_config():
    config_dir = get_config_dir()
    if not os.path.exists(config_dir):
        logger.error("Config not found. Have you run setup? Try golfhelper --help for details")
        return
    else:
        with open(os.path.join(config_dir, CONFIG_FILE_NAME), 'r') as config:
            data = yaml.safe_load(config)
        return data


if __name__ == '__main__':
    init()
