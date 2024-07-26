## [Minspeech](https://minspeech.github.io/)

A Corpus of Southern Min Dialect for Automatic Speech Recognition

[**Official website**](https://minspeech.github.io/)

## Resource
Let's start with obtaining the [resource](https://drive.google.com/drive/folders/1tGurSeeWALcBKKmmpKQQq7p4s-1o-Vce) files.

## File structure
```
% The file structure is summarized as follows:
|---- crop.py	# extract speech/video segments by timestamps from downloaded videos
|---- download.py	# download audios by audio_list
|---- LICENSE		# license
|---- README.md	
|---- requirement.txt			
|---- resource               # resource folder
      |---- label
            |---- list       # video_list for downloading audios
            |---- data       # [utt] train,dev,test
                  |---- train_text	
                  |---- train_wav.scp
                  |---- dev_text	
                  |---- dev_wav.scp
                  |---- test_text	
                  |---- test_wav.scp
       |---- unlabel
            |---- list       # video_list for downloading audios
```

## Download

### Install ffmpeg

``` bash
sudo apt-get update && sudo apt-get upgrade
sudo apt-get install ffmpeg
``` 

### Clone Repo

``` bash
git clone https://github.com/Minspeech/minspeech.git
```

### Install Python library

``` bash
python3 -m pip install -r requirements.txt
```

### Download

``` bash
python download.py
```

### Crop

For labeled audio, use the script we provide to cut the audio, and for unlabeled audio, use the [silero-vad](https://github.com/snakers4/silero-vad) toolkit to cut it.

``` bash
python crop.py
```

## License
The dataset is licensed under the CC BY-NC-SA 4.0 license. This means that you can share and adapt the dataset for non-commercial purposes as long as you provide proper attribution and distribute your contributions under the same license.

Important: The dataset we release contains only annotated data, including YouTube links and transcription labels. We do not release audio or video data, and it is the responsibility of users to decide whether and how to download video data, and whether their intended purpose of downloading the data is legal in their country.
