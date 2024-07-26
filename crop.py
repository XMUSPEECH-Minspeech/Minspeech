import os
import re
import pandas as pd
import numpy as np
import zhconv
import wave
from scipy.io import wavfile
from scipy.signal import resample
from moviepy.audio.AudioClip import AudioArrayClip
from moviepy.editor import *
from time import time
import statistics

# Some short audio files (less than 0.2s) might still be created; they will need to be manually deleted later.

# Parameters that need to be modified
SourceDir = "./SourceData/label/"
OutputDir = "./OutputData/label/"

output_file = ""
source_file = ""
s0s1 = ""
Episode = ""
all_time = 0  # Initialize total time
filter_chinese = re.compile("[^\u4e00-\u9fa5^0-9]")  # Match Chinese characters and numbers
filter_a_z = re.compile("[^a-z^A-Z^\u0025]")  # Match letters and '%'
filter_bracket = re.compile("[^(^)^（^）^×^÷^-^*^+]")
punctuation = ",.?!:，\\。！~？/：、…“”\""
re_punctuation = "[{}]+".format(punctuation)

def split_wav(df, source_wav_path):
    """
    Split the audio based on start and end times from the dataframe, and save the resulting clips and captions.
    :param df: DataFrame with start/end times and captions
    :param source_wav_path: Path to the source audio file
    """
    # Read the audio file
    wavread = wave.open(source_wav_path, 'rb')
    wav_params = wavread.getparams()
    sampling_rate = wav_params[2]
    assert sampling_rate == 16000  # Ensure the sample rate is 16000 Hz
    wav_bytes = wavread.readframes(wav_params[3])
    assert wav_params[1] == 2  # Ensure audio is 2 channels
    wave_data = np.frombuffer(wav_bytes, dtype=np.int16)
    wave_data = np.reshape(wave_data, [wav_params[3], wav_params[0]])[:, 0]  # Use only one channel

    # Convert times in df to frames
    start_time_column = pd.to_numeric(df["start_time"])
    start_frame_column = np.ceil(start_time_column * sampling_rate).astype(int)
    end_time_column = pd.to_numeric(df["end_time"])
    end_frame_column = np.ceil(end_time_column * sampling_rate).astype(int)
    df['start_frame'] = start_frame_column
    df['end_frame'] = end_frame_column
    df = df.drop(['start_time', "end_time"], axis=1)

    # Open text files for writing the results
    all_text = open(output_file[:-4] + "text", 'a', encoding='utf-8')
    all_wavscp = open(output_file[:-4] + "wav.scp", "a", encoding="utf-8")
    
    # Cut audio and save clips and captions
    for i in range(len(end_frame_column)):
        wavfile.write(output_file + "audio/" + df["ID"][i][3:6] + "/" + df["ID"][i] + ".wav", sampling_rate, wave_data[df["start_frame"][i]: df["end_frame"][i]])
        all_wavscp.write(df["ID"][i] +" " + output_file + "audio/" + df["ID"][i][3:6] + "/" + df["ID"][i] + ".wav" + "\n")
        all_text.write(df["ID"][i] + " " + df["caption"][i] + "\n")
    all_text.close()
    wavread.close()
    print("Episode " + source_wav_path[-10:-4] + " done.\n")

def vtt2list(full_path):
    """
    Convert a .vtt file to a DataFrame with start/end times and captions.
    :param full_path: Path to the .vtt file
    :return: DataFrame with start/end times, captions, and IDs
    """
    global all_time
    with open(full_path, mode='r', encoding='utf-8') as f:
        f_str = f.read()
        lines = f_str.split("\n")[4:]  # Skip the first 4 lines (metadata)
        lines = [line for line in lines if line]  # Remove empty lines

        # Remove invalid subtitle lines
        del_lines = [i for i in range(len(lines) - 1) if not (" --> " in lines[i]) and not (" --> " in lines[i + 1])]
        for i in reversed(del_lines):
            del lines[i:i+3]

        start_times, end_times, captions, lasts = [], [], [], []

        for i, line in enumerate(lines):
            if i % 2:  # Odd lines contain captions
                text = zhconv.convert(line, 'zh-hans')  # Convert traditional to simplified Chinese
                a_z = filter_a_z.sub("", text.strip())  # Remove letters and '%'
                bracket = filter_bracket.sub("", text.strip())
                text = re.sub(re_punctuation, "", text)  # Remove punctuation
                if len(text.replace(" ","")) <= 2 or continue_time < 0.2 or continue_time > 7 or bracket or a_z:
                    lasts.pop()
                    start_times.pop()
                    end_times.pop()
                    continue
                captions.append(text)
            else:  # Even lines contain time codes
                try:
                    s_time = float(line[:2]) * 3600 + float(line[3:5]) * 60 + float(line[6:12])
                    e_time = float(line[17:19]) * 3600 + float(line[20:22]) * 60 + float(line[23:29])
                    continue_time = e_time - s_time
                    all_time += continue_time
                    lasts.append(continue_time)
                    start_times.append(s_time)
                    end_times.append(e_time)
                except ValueError:  # Handle invalid time codes
                    continue_time = 0
                    all_time += continue_time
                    lasts.append(continue_time)
                    start_times.append(s_time)
                    end_times.append(e_time)

        intervals = [start_times[i + 1] - end_times[i] for i in range(len(end_times) - 1)] + [0]
        median = statistics.median(intervals)
        df = pd.DataFrame({'start_time': start_times, "end_time": end_times, "interval": intervals, "last_time": lasts, "caption": captions})

        # Add unique IDs
        df['ID'] = [full_path[-10:-4] + str(num).zfill(4) for num in range(len(df['caption']))]
        return df

def create_path(dirname):
    """
    Create a directory if it doesn't exist.
    """
    if not os.path.exists(dirname):
        os.makedirs(dirname)

def make_file_set():
    """
    Ensure each episode has both a .vtt and .wav file, and return the set of episodes.
    """
    episode_list = []
    missing_episodes = []
    for episode in os.listdir(source_file):
        assert episode[1:3] == s0s1  # Ensure the episode belongs to the correct series
        episode_list.append(episode[-7:-4])
    for episode in episode_list:
        if episode_list.count(episode) != 2:
            assert episode_list.count(episode) == 1  # Ensure each episode appears exactly twice (one .vtt and one .wav)
            print("Episode {} is missing subtitle/audio file".format(episode))
            missing_episodes.append(episode)
    for episode in missing_episodes:
        episode_list.remove(episode)
    return sorted(set(episode_list))

def main():
    global source_file, output_file
    source_file = SourceDir + "S{}/".format(s0s1)
    output_file = OutputDir + "S{}/".format(s0s1)
    create_path(output_file)
    create_path(output_file + "/audio")

    episodes_set = make_file_set()
    print("Available episodes for S{}: {}".format(s0s1, episodes_set))

    for episode in episodes_set:
        create_path(output_file + "/audio/" + episode)
        Episode = episode
        times_captions_df = vtt2list(source_file + "S" + s0s1 + str(episode).zfill(3) + ".vtt")
        split_wav(times_captions_df, source_file + "S" + s0s1 + str(episode).zfill(3) + ".wav")

if __name__ == "__main__":
    for dir_name in os.listdir(SourceDir):
        assert len(dir_name) == 3  # Ensure directory name is in Ss0s1 format
        s0s1 = dir_name[1:]
        print(dir_name)
        main()
    print("Total duration: ", all_time / 3600)
