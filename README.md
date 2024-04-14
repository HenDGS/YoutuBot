# YoutuBot
<a id="readme-top"></a>

<div align="center">
  <img src="https://i.imgur.com/VHsP1Sl.png" width="512" height="512">
</div>

<!-- TABLE OF CONTENTS -->
## Table of Contents

<details>
  <summary>Index</summary>
    <ol>
        <li>
        <a href="#about-the-project">About The Project</a>
        </li>      
        <li>
        <a href="#how-to-use">Commands</a>
        </li>
        <li>
        <a href="#how-to-run">How To Run</a>
        </li>
        <li>
        <a href="#to-do">To Do</a>
        </li>
    </ol>
</details>

<!-- ABOUT THE PROJECT -->
<a id="about-the-project"></a>
## About The Project

A selfhosted Discord bot to play Youtube (and other websites supported by yt-dlp; see https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md) videos on voice chat. 

<p style="text-align: right;">(<a href="#readme-top">back to top</a>)</p>

<!-- HOW TO USE -->
<a id="how-to-use"></a>
## Commands

**Play**: Pass a url or a search string to add a video to the queue and make the bot join the the voice channel.

**Stop**: Makes the bot stop playing the current video, and clears the queue.

**Skip**: Skips the current video being played.

**Queue**: Send a message with the videos in the queue.

<p style="text-align: right;">(<a href="#readme-top">back to top</a>)</p>

<!-- HOW TO RUN FROM SOURCE -->
<a id="how-to-run"></a>
## How To Run

1: Clone or download this repository;

2: In the Discord Developer Portal create an application;

3: Get a bot token;

3: Create a .env with the bot token in the bot folder;

4: Run this command to install the requirements (using a venv is recommended):
```bash 
pip install -r requirements.txt
```
5: Run the bot.
```bash
python src/main.py
```

<p style="text-align: right;">(<a href="#readme-top">back to top</a>)</p>

<!-- To Do -->
<a id="to-do"></a>
## To Do

- [ ] Add support for playlists
- [ ] Make a video tutorial on how to run the bot
- [ ] Add interactive buttons for commands

<p style="text-align: right;">(<a href="#readme-top">back to top</a>)</p>
