import ffmpeg
import click
import os
import logging
import yaml
import datetime
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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
@click.command()
@click.option('--root', prompt='Root directory to use', help='Root directory for golf videos')
@click.option('--max-video-size-mb', default=5)
def setup_tool(root, max_video_size_mb):
    """
    Creates a config file with where the root directory should be stored.
    """
    config_dir = get_config_dir()
    if not os.path.exists(config_dir):
        logging.info("Config not found. Creating directory at: {}".format(config_dir))
        os.makedirs(config_dir)
    with open(os.path.join(config_dir, CONFIG_FILE_NAME), 'w') as config:
        logging.info("Configuring golf helper root directory to: {}".format(root))
        data = {
            CONFIG_KEYS.ROOT: root,
            CONFIG_KEYS.MAX_VIDEO_SIZE_MB: max_video_size_mb
        }
        yaml.dump(data, config, default_flow_style=False)
    logging.info("Finished setup!")


@click.command()
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
    config = get_config()
    root_dir = config[CONFIG_KEYS.ROOT]
    max_video_size_bytes = config[CONFIG_KEYS.MAX_VIDEO_SIZE_MB] * 1024 * 1024

    if not video.lower().endswith('.mov') and not video.lower().endswith('.mp4'):
        logging.error("Video provided is not a supported format.")
        return
    # Create directory for our new videos along with directory for analysis
    date = datetime.now().strftime('%y-%m-%d')
    new_golf_dir = os.paht.join(root_dir, date)
    golf_video_dir = os.path.join(new_golf_dir, 'videos')
    golf_analysis_dir = os.path.join(new_golf_dir, 'analyze')
    os.makedirs(new_golf_dir, exist_ok=True)
    os.makedirs(golf_video_dir, exist_ok=True)
    os.makedirs(golf_analysis_dir, exist_ok=True)

    counter = 0
    output_file=os.path.join(golf_video_dir, club + counter + ".mp4")
    while os.path.exists(output_file):
        counter += 1
        output_file = os.path.join(golf_video_dir, club + counter + ".mp4")
    # Convert video to mp4 format
    if video.lower().endswith('.mov'):
        (
            ffmpeg
                .input(video)
                .output(output_file, **{'c:v': 'copy', 'c:a': 'copy'})
                .run(overwrite_output=True)
        )
        video = output_file
    # Compress video if necessary
    video_size = os.path.getsize(video)
    if video_size > max_video_size_bytes:
        (
            ffmpeg
                .input(video)
                .output(output_file, vf='scale=iw/2:-1', strict='-2')
                .run(overwrite_output=True)
        )
        

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
        logging.error("Config not found. Have you run setup? Try golfhelper --help for details")
        return
    else:
        with open(os.path.join(config_dir, CONFIG_FILE_NAME), 'r') as config:
            data = yaml.safe_load(config)
        return data


if __name__ == '__main__':
    setup_tool()
    organize()
