import yt_dlp
import time, argparse, os, json
from tqdm import tqdm
import multiprocessing as mp
from multiprocessing import Manager
import random, logging, sys
import zhconv
import re

logging.basicConfig(level=logging.INFO)  # Configure logging level to INFO

# Argument parser setup
parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--base_dir', 
                    default='SourceData', 
                    type=str,
                    help="Directory to save audio files")
parser.add_argument('--num_workers', 
                    default=3, 
                    type=int,
                    help="Number of workers for multiprocessing to facilitate the download process")
parser.add_argument('--labeled', 
                    default='True', 
                    help="Use labeled data if set, otherwise use unlabeled data")
args = parser.parse_args()

# Convert Traditional Chinese text to Simplified Chinese
def traditional_to_simplified(traditional_text):
    return zhconv.convert(traditional_text, 'zh-hans')

# Remove all punctuation from text
def remove_punctuation(text):
    return re.sub(r'[^\w\s]', '', text)

# Convert subtitle file content from Traditional Chinese to Simplified Chinese and remove punctuation
def convert_subtitle_to_simplified(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    simplified_lines = []
    for line in lines:
        simplified_line = traditional_to_simplified(line)
        if '-->' not in simplified_line and not simplified_line.startswith(('WEBVTT', 'Kind:', 'Language:')):
            simplified_line = remove_punctuation(simplified_line)
        simplified_lines.append(simplified_line)
    
    with open(file_path, 'w', encoding='utf-8') as file:
        file.writelines(simplified_lines)
    
# Download audio and subtitles from YouTube
def job_audio(urls, series, series_path, downloaded_urls):
    base_dir = os.path.join(os.getcwd(), args.base_dir, series_path, series)
    os.makedirs(base_dir, exist_ok=True)
    existing_files = [f for f in os.listdir(base_dir) if f.endswith('.wav')]
    file_num = 1
    
    for url in urls:
        file_num_str = f"{file_num:03}"
        output_template = os.path.join(base_dir, f"{series}{file_num_str}")
        wav_file = f"{output_template}.wav"
        vtt_file = f"{output_template}.vtt"
        
        # Check if files already exist to support resumable download
        if os.path.exists(wav_file) and os.path.exists(vtt_file):
            file_num += 1
            downloaded_urls.append(url)
            continue
        elif os.path.exists(wav_file) and not os.path.exists(vtt_file):
            os.remove(wav_file)
            downloaded_urls.append(url)
        elif not os.path.exists(wav_file) and os.path.exists(vtt_file):
            os.remove(vtt_file)
            downloaded_urls.append(url)
        elif url in downloaded_urls:
            continue
        else:
            downloaded_urls.append(url)
        
        try:
        # Options for downloading audio
            ydl_opts_audio = {
                'format': 'bestaudio',
                'outtmpl': output_template,
                'noplaylist': True,
                'ignoreerrors': True,
                'max_sleep_interval': 0.2,
                'verbose': False,
                'quiet': True,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'wav',
                    'preferredquality': '192',
                }],
                'postprocessor_args': [
                    '-ar', '16000',
                    '-strict', '-2',
                    '-async', '1', '-r', '25'
                ],
            }
        
            # Download audio
            with yt_dlp.YoutubeDL(ydl_opts_audio) as ydl:
                error_code = ydl.download([url])
            
            # Ensure the file has the correct .wav extension
            if not wav_file.endswith('.wav'):
                os.rename(wav_file, wav_file + '.wav')

            # Options for downloading subtitles
            ydl_opts_sub = {
                'writesubtitles': True,
                'subtitleslangs': ['zh-TW'],
                'skip_download': True,
                'outtmpl': vtt_file
            }
            
            # Download subtitles
            with yt_dlp.YoutubeDL(ydl_opts_sub) as ydl:
                error_code = ydl.download([url])
            
            # Rename the subtitle file to remove the language suffix if it exists
            if os.path.exists(f"{vtt_file}.zh-TW.vtt"):
                os.rename(f"{vtt_file}.zh-TW.vtt", vtt_file)

            # Convert subtitles to Simplified Chinese and remove punctuation
            if os.path.exists(vtt_file):
                convert_subtitle_to_simplified(vtt_file)
            
        except Exception as e:
            logging.error(f"Failed to download {url}: {str(e)}")
        
        file_num += 1

# Split dictionary into multiple chunks for parallel processing
def split_dict(data, num_splits):
    keys = list(data.keys())
    random.shuffle(keys)
    split_keys = [keys[i::num_splits] for i in range(num_splits)]
    return [{k: data[k] for k in subset} for subset in split_keys]

# Download process
def download(episodeaudio, series_path, downloaded_urls):
    for series, audio in episodeaudio.items():
        os.makedirs(os.path.join(os.getcwd(), args.base_dir, series_path, series), exist_ok=True)
        job_audio(audio, series, series_path, downloaded_urls)

if __name__ == '__main__':
    print("*" * 15)
    print("* Download Starts *")
    print("*" * 15)
    os.makedirs(os.path.join(os.getcwd(), args.base_dir), exist_ok=True)

    # Define paths for labeled and unlabeled data
    label_path = r"resource/label/list"
    unlabel_path = r"resource/unlabel/list"

    # Set the episode audio list location based on whether the data is labeled or not
    episodeaudio_loc = label_path if args.labeled == 'True' else unlabel_path
    # Determine the series path based on whether the data is labeled or not
    series_path = 'label' if args.labeled == 'True' else 'unlabel'

    # Check if the episode audio list file exists
    if not os.path.exists(episodeaudio_loc):
        logging.error("Audio list does not exist!!")
        sys.exit()

    # Load audio list from file
    episodeaudio = {line.split()[0]: line.strip().split()[1:] for line in open(episodeaudio_loc)}

    # Determine number of workers for multiprocessing
    workers = min(args.num_workers, len(episodeaudio))
    episodeaudio_slices = split_dict(episodeaudio, workers)

    # Create a pool of worker processes for downloading
    manager = Manager()
    downloaded_urls = manager.list()
    pool = mp.Pool(processes=workers)
    pool.starmap(download, [(slice, series_path, downloaded_urls) for slice in episodeaudio_slices])
    pool.close()
    pool.join()
