import asyncio
import os
from typing import Optional
import discord
from discord.ext import commands
from dotenv import load_dotenv
import yt_dlp
from collections import deque


class Bot(commands.Bot):
    def __init__(self, command_prefix: str, intents: discord.Intents) -> None:
        super().__init__(command_prefix=command_prefix, intents=intents)
        self.queue: deque[str] = deque()
        self.running_queue: bool = False
        self.voice_clients_map: dict[discord.VoiceChannel, discord.VoiceClient] = {}

    async def join_vc(self, ctx: commands.Context) -> discord.VoiceClient or None:
        if not ctx.author.voice:
            await ctx.send('Join a voice channel first, you fool!')
            return

        voice_channel: discord.VoiceChannel = ctx.author.voice.channel
        voice: discord.VoiceClient = discord.utils.get(self.voice_clients, channel=voice_channel)
        if voice is None:
            voice: discord.VoiceClient = await voice_channel.connect()
        return voice

    async def play_video(self, ctx: commands.Context, url: str, voice: discord.VoiceClient) -> None:
        ydl_opts: dict[str, any] = {
            'source_address': '0.0.0.0',
            'format': 'bestaudio/best',
            'noplaylist': 'True',
            'default_search': 'ytsearch',
            'buffersize': '2048',
        }
        ffmpeg_options: dict[str, str] = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                                          'options': '-vn'}

        ytdl: yt_dlp.YoutubeDL = yt_dlp.YoutubeDL(ydl_opts)

        try:
            info: dict[str, any] = ytdl.extract_info(url, download=False)
        except yt_dlp.DownloadError:
            await ctx.send(f'Url not supported, {ctx.author.name}!')
            return

        if 'entries' in info:
            try:
                info: dict[str, any] = info['entries'][0]
            except IndexError:
                await ctx.send(f"Couldn't find this url, {ctx.author.name}!")
                return

        def after(e: Exception) -> None:
            if self.queue:
                last_url: str = self.queue.popleft()
                asyncio.run_coroutine_threadsafe(self.play_video(ctx, last_url, voice), self.loop)
            else:
                self.running_queue = False
                print(f'Error: {e}')

        await ctx.send(f'Video: **{info["title"]}**')
        voice.play(discord.FFmpegOpusAudio(info['url'], **ffmpeg_options),
                   after=after)

    async def play_queue(self, ctx: commands.Context, url: str, voice: discord.VoiceClient) -> None:
        self.queue.append(url)

        if self.queue and self.running_queue:
            await ctx.send(f'Added {url} to the queue!')

        if not self.running_queue:
            self.running_queue = True
            url: str = self.queue.popleft()
            await self.play_video(ctx, url, voice)


def main(token: str) -> None:
    bot: Bot = Bot(command_prefix="/", intents=discord.Intents.default())

    @bot.event
    async def on_ready() -> None:
        print(f'Logged in as {bot.user}')
        await bot.tree.sync()

    @bot.event
    async def on_message(message: discord.Message) -> None:
        if message.author == bot.user:
            return

    @bot.event
    async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
        await ctx.send(f'An error occurred: {str(error)}')

    @bot.hybrid_command(name="play", description="Play a video from a url or add it to the queue")
    async def play(ctx: commands.Context, url: str) -> None:
        await ctx.defer()

        vc: Optional[discord.VoiceClient] = await bot.join_vc(ctx)
        if not vc:
            return

        await bot.play_queue(ctx, url, vc)

    @bot.hybrid_command(name="stop", description="Stops the current video and clears the queue")
    async def stop(ctx: commands.Context) -> None:
        voice: Optional[discord.VoiceClient] = await bot.join_vc(ctx)
        if voice and voice.is_playing():
            voice.stop()
            bot.queue.clear()
            await ctx.send("Stopped the music and cleared the queue.")

    @bot.hybrid_command(name="skip", description="Skips the current video")
    async def skip(ctx: commands.Context) -> None:
        voice: Optional[discord.VoiceClient] = await bot.join_vc(ctx)
        if voice and voice.is_playing():
            voice.stop()
            await ctx.send("Skipped the current video.")

    @bot.hybrid_command(name="queue", description="Shows the current queue")
    async def queue(ctx: commands.Context) -> None:
        if bot.queue:
            await ctx.send(f"Current queue: {', '.join(bot.queue)}")
        else:
            await ctx.send("The queue is empty!")

    bot.run(token)


if __name__ == '__main__':
    load_dotenv()
    main(os.getenv('DISCORD_TOKEN'))
