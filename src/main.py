import asyncio
import os
from typing import Optional
import discord
from discord import ui
from discord.ext import commands
from dotenv import load_dotenv
import yt_dlp
from collections import deque
import logging
import gc


class MusicControlView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @ui.button(label="⏸️ Pause", style=discord.ButtonStyle.primary, custom_id="pause_button")
    async def pause_button(self, interaction: discord.Interaction, button: ui.Button):
        voice = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
        if voice and voice.is_playing():
            voice.pause()
            await interaction.response.send_message("⏸️ Paused", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing is playing!", ephemeral=True)
    
    @ui.button(label="▶️ Resume", style=discord.ButtonStyle.success, custom_id="resume_button")
    async def resume_button(self, interaction: discord.Interaction, button: ui.Button):
        voice = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
        if voice and voice.is_paused():
            voice.resume()
            await interaction.response.send_message("▶️ Resumed", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing is paused!", ephemeral=True)
    
    @ui.button(label="⏭️ Skip", style=discord.ButtonStyle.secondary, custom_id="skip_button")
    async def skip_button(self, interaction: discord.Interaction, button: ui.Button):
        voice = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
        if voice and (voice.is_playing() or voice.is_paused()):
            voice.stop()
            await interaction.response.send_message("⏭️ Skipped", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing is playing!", ephemeral=True)
    
    @ui.button(label="⏹️ Stop", style=discord.ButtonStyle.danger, custom_id="stop_button")
    async def stop_button(self, interaction: discord.Interaction, button: ui.Button):
        voice = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
        if voice and (voice.is_playing() or voice.is_paused()):
            voice.stop()
            self.bot.queue.clear()
            self.bot.running_queue = False
            await interaction.response.send_message("⏹️ Stopped and cleared queue", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing is playing!", ephemeral=True)
    
    @ui.button(label="📜 Queue", style=discord.ButtonStyle.secondary, custom_id="queue_button")
    async def queue_button(self, interaction: discord.Interaction, button: ui.Button):
        if self.bot.queue:
            embed = discord.Embed(title="📜 Queue", color=discord.Color.blue())
            queue_list = '\n'.join([f"`{i+1}.` {video.get('title', 'Unknown')[:60]}" 
                                   for i, video in enumerate(list(self.bot.queue)[:10])])
            embed.description = queue_list
            
            if len(self.bot.queue) > 10:
                embed.set_footer(text=f"... and {len(self.bot.queue) - 10} more songs")
            else:
                embed.set_footer(text=f"Total: {len(self.bot.queue)} songs")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("📭 The queue is empty!", ephemeral=True)


class Bot(commands.Bot):
    def __init__(self, command_prefix: str, intents: discord.Intents) -> None:
        super().__init__(command_prefix=command_prefix, intents=intents)
        self.queue: deque[dict] = deque()
        self.running_queue: bool = False
        self.voice_clients_map: dict[discord.VoiceChannel, discord.VoiceClient] = {}
        self.logger = logging.getLogger('discord.bot')
        self.current_player_message: Optional[discord.Message] = None
        self._video_cache: dict[str, dict] = {}
        self._cache_limit = 50

    async def join_vc(self, ctx: commands.Context) -> discord.VoiceClient or None:
        if not ctx.author.voice:
            await ctx.send('Join a voice channel first, you fool!')
            return

        voice_channel: discord.VoiceChannel = ctx.author.voice.channel
        voice: discord.VoiceClient = discord.utils.get(self.voice_clients, channel=voice_channel)
        if voice is None:
            voice: discord.VoiceClient = await voice_channel.connect()
        return voice

    async def extract_info(self, url: str, extract_flat: bool = False) -> tuple[Optional[dict], Optional[str]]:
        cache_key = f"{url}_{extract_flat}"
        if cache_key in self._video_cache and not extract_flat:
            self.logger.info(f"Cache hit for {url}")
            return self._video_cache[cache_key], None
        
        ydl_opts: dict[str, any] = {
            'source_address': '0.0.0.0',
            'format': 'bestaudio/best',
            'noplaylist': False,
            'default_search': 'ytsearch',
            'extract_flat': extract_flat,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'no_color': True,
            'extractor_retries': 1,
            'skip_download': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ytdl:
                info = await asyncio.to_thread(ytdl.extract_info, url, download=False)
                
                if info and not extract_flat:
                    if len(self._video_cache) >= self._cache_limit:
                        self._video_cache.pop(next(iter(self._video_cache)))
                    self._video_cache[cache_key] = info
                
                return info, None
        except yt_dlp.DownloadError as e:
            error_msg = str(e).lower()
            if 'sign in' in error_msg or 'age' in error_msg or 'private' in error_msg:
                return None, "age_restricted"
            elif 'not available' in error_msg or 'removed' in error_msg:
                return None, "unavailable"
            self.logger.error(f"yt-dlp error: {e}")
            return None, "download_error"
        except Exception as e:
            self.logger.error(f"Unexpected error extracting info: {e}")
            return None, "unknown_error"

    def create_now_playing_embed(self, video_info: dict) -> discord.Embed:
        title = video_info.get('title', 'Unknown')
        if len(title) > 100:
            title = title[:97] + "..."
        
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**[{title}]({video_info.get('webpage_url', '')})**",
            color=discord.Color.green()
        )
        
        thumbnail = video_info.get('thumbnail')
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        
        uploader = video_info.get('uploader')
        if uploader:
            if len(uploader) > 50:
                uploader = uploader[:47] + "..."
            embed.add_field(name="Channel", value=uploader, inline=True)
        
        duration = video_info.get('duration')
        if duration:
            minutes, seconds = divmod(duration, 60)
            hours, minutes = divmod(minutes, 60)
            duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"
            embed.add_field(name="Duration", value=duration_str, inline=True)
        
        embed.set_footer(text=f"Queue: {len(self.queue)} songs")
        
        return embed

    async def play_video(self, ctx: commands.Context, video_info: dict, voice: discord.VoiceClient) -> None:
        if voice.is_playing():
            self.logger.warning(f"Already playing audio, cannot start: {video_info.get('title')}")
            return
        
        if voice.is_paused():
            voice.stop()
            await asyncio.sleep(0.5)
        
        ffmpeg_options: dict[str, str] = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -probesize 32M -analyzeduration 0',
            'options': '-vn -b:a 128k'
        }

        async def play_next():
            if self.queue:
                await asyncio.sleep(0.3)
                if not voice.is_playing():
                    next_video = self.queue.popleft()
                    await self.play_video(ctx, next_video, voice)
            else:
                self.running_queue = False

        def after(e: Optional[Exception]) -> None:
            if e:
                self.logger.error(f'Player error: {e}')
            
            asyncio.run_coroutine_threadsafe(play_next(), self.loop)

        try:
            embed = self.create_now_playing_embed(video_info)
            view = MusicControlView(self)
            self.current_player_message = await ctx.send(embed=embed, view=view)
            voice.play(discord.FFmpegOpusAudio(video_info['url'], **ffmpeg_options), after=after)
            
            if 'formats' in video_info:
                del video_info['formats']
            if 'thumbnails' in video_info:
                del video_info['thumbnails']
            if 'automatic_captions' in video_info:
                del video_info['automatic_captions']
            if 'subtitles' in video_info:
                del video_info['subtitles']
        except discord.ClientException as e:
            self.logger.error(f"Discord client error: {e}")
            await ctx.send(f"❌ Audio player error: {str(e)}")
            self.running_queue = False
        except Exception as e:
            self.logger.error(f"Error playing video: {e}")
            await ctx.send(f"❌ Failed to play: {video_info.get('title', 'Unknown')}")
            if self.queue and not voice.is_playing():
                next_video = self.queue.popleft()
                await self.play_video(ctx, next_video, voice)
            else:
                self.running_queue = False

    async def add_to_queue(self, ctx: commands.Context, url: str, voice: discord.VoiceClient) -> None:
        loading_msg = await ctx.send("🔍 Fetching video information...")
        
        info, error = await self.extract_info(url, extract_flat=True)
        
        if not info:
            if error == "age_restricted":
                await loading_msg.edit(content=f'🔞 This video is age-restricted or requires sign-in. The bot cannot play it without authentication.')
            elif error == "unavailable":
                await loading_msg.edit(content=f'❌ This video is unavailable, private, or has been removed.')
            else:
                await loading_msg.edit(content=f'❌ URL not supported or couldn\'t fetch info, {ctx.author.mention}!')
            return

        is_playlist = 'entries' in info
        playlist_info = []
        
        if is_playlist:
            playlist_title = info.get('title', 'Unknown Playlist')
            entries = [e for e in info['entries'] if e]
            
            if not entries:
                await loading_msg.edit(content="❌ No videos found in this playlist!")
                return
            
            embed = discord.Embed(
                title="📋 Loading Playlist",
                description=f"**{playlist_title}**\nAdding {len(entries)} videos...",
                color=discord.Color.blue()
            )
            await loading_msg.edit(content=None, embed=embed)
            
            for entry in entries:
                video_url = entry.get('url') or f"https://www.youtube.com/watch?v={entry['id']}"
                playlist_info.append({
                    'url': video_url,
                    'title': entry.get('title', 'Unknown')
                })
        else:
            if 'url' not in info:
                info, error = await self.extract_info(url, extract_flat=False)
            
            if info and 'url' in info:
                lightweight_info = {
                    'url': info['url'],
                    'title': info.get('title', 'Unknown'),
                    'webpage_url': info.get('webpage_url', ''),
                    'thumbnail': info.get('thumbnail', ''),
                    'uploader': info.get('uploader', ''),
                    'duration': info.get('duration', 0)
                }
                self.queue.append(lightweight_info)
                
                if self.running_queue:
                    embed = discord.Embed(
                        title="✅ Added to Queue",
                        description=f"**[{lightweight_info['title']}]({lightweight_info.get('webpage_url', '')})**",
                        color=discord.Color.green()
                    )
                    if lightweight_info.get('thumbnail'):
                        embed.set_thumbnail(url=lightweight_info['thumbnail'])
                    embed.add_field(name="Position", value=f"#{len(self.queue)}", inline=True)
                    if lightweight_info.get('duration'):
                        minutes, seconds = divmod(lightweight_info['duration'], 60)
                        embed.add_field(name="Duration", value=f"{minutes:02d}:{seconds:02d}", inline=True)
                    await loading_msg.edit(content=None, embed=embed)
                else:
                    self.running_queue = True
                    await loading_msg.delete()
                    await self.play_video(ctx, lightweight_info, voice)
            else:
                if error == "age_restricted":
                    await loading_msg.edit(content='🔞 This video is age-restricted. The bot cannot play it without YouTube account authentication.')
                elif error == "unavailable":
                    await loading_msg.edit(content='❌ This video is unavailable, private, or has been removed.')
                else:
                    await loading_msg.edit(content="❌ Couldn't fetch video info!")
            return

        added_count = 0
        skipped_count = 0
        age_restricted_count = 0
        first_video = None
        
        batch_size = 3
        for batch_start in range(0, len(playlist_info), batch_size):
            batch = playlist_info[batch_start:batch_start + batch_size]
            
            tasks = [self.extract_info(vid['url'], extract_flat=False) for vid in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for idx, (video_data, result) in enumerate(zip(batch, results)):
                if isinstance(result, Exception):
                    skipped_count += 1
                    self.logger.warning(f"Exception processing video: {result}")
                    continue
                
                video_info, error = result
                
                if video_info and 'url' in video_info:
                    lightweight_info = {
                        'url': video_info['url'],
                        'title': video_info.get('title', 'Unknown'),
                        'webpage_url': video_info.get('webpage_url', ''),
                        'thumbnail': video_info.get('thumbnail', ''),
                        'uploader': video_info.get('uploader', ''),
                        'duration': video_info.get('duration', 0)
                    }
                    
                    if first_video is None and not self.running_queue:
                        first_video = lightweight_info
                    else:
                        self.queue.append(lightweight_info)
                    added_count += 1
                else:
                    if error == "age_restricted":
                        age_restricted_count += 1
                        self.logger.warning(f"Skipped age-restricted video: {video_data['title']}")
                    else:
                        skipped_count += 1
                        self.logger.warning(f"Skipped invalid video: {video_data['url']}")
            
            current_pos = batch_start + len(batch)
            if current_pos % 15 == 0 or current_pos == len(playlist_info):
                status = f"**{playlist_title}**\nAdded {added_count}/{len(playlist_info)} videos..."
                if skipped_count > 0:
                    status += f"\n⚠️ Skipped {skipped_count} (unavailable/private)"
                if age_restricted_count > 0:
                    status += f"\n🔞 Skipped {age_restricted_count} (age-restricted)"
                embed.description = status
                try:
                    await loading_msg.edit(embed=embed)
                except discord.HTTPException:
                    pass

        if added_count == 0:
            error_msg = "❌ No valid videos could be added!"
            if age_restricted_count > 0:
                error_msg += f"\n🔞 {age_restricted_count} videos were age-restricted (bot needs YouTube account)"
            if skipped_count > 0:
                error_msg += f"\n⚠️ {skipped_count} videos were unavailable/private"
            await loading_msg.edit(content=error_msg, embed=None)
            return

        embed = discord.Embed(
            title="✅ Playlist Added",
            description=f"**{playlist_title}**\nSuccessfully added {added_count} videos!",
            color=discord.Color.green()
        )
        
        if skipped_count > 0 or age_restricted_count > 0:
            warnings = []
            if skipped_count > 0:
                warnings.append(f"⚠️ {skipped_count} unavailable/private")
            if age_restricted_count > 0:
                warnings.append(f"🔞 {age_restricted_count} age-restricted")
            embed.add_field(name="Skipped", value=" | ".join(warnings), inline=False)
        
        embed.add_field(name="Queue Size", value=f"{len(self.queue)} songs", inline=True)
        await loading_msg.edit(content=None, embed=embed)
        
        if first_video:
            self.running_queue = True
            self.logger.info(f"Starting playlist playback with: {first_video.get('title')}")
            await self.play_video(ctx, first_video, voice)
        elif not self.running_queue and self.queue:
            self.running_queue = True
            first_video = self.queue.popleft()
            self.logger.info(f"Starting playlist from queue: {first_video.get('title')}")
            await self.play_video(ctx, first_video, voice)
        
        gc.collect()


def main(token: str) -> None:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = False
    intents.presences = False
    
    bot: Bot = Bot(command_prefix="/", intents=intents)

    @bot.event
    async def on_ready() -> None:
        print(f'Logged in as {bot.user}')
        print(f'Memory-optimized mode enabled')
        await bot.tree.sync()

    @bot.event
    async def on_message(message: discord.Message) -> None:
        if message.author == bot.user:
            return
        await bot.process_commands(message)

    @bot.event
    async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
        await ctx.send(f'An error occurred: {str(error)}')

    @bot.hybrid_command(name="play", description="Play a video/playlist from URL or search query")
    async def play(ctx: commands.Context, *, url: str) -> None:
        await ctx.defer()

        vc: Optional[discord.VoiceClient] = await bot.join_vc(ctx)
        if not vc:
            return

        await bot.add_to_queue(ctx, url, vc)

    @bot.hybrid_command(name="stop", description="Stops the current video and clears the queue")
    async def stop(ctx: commands.Context) -> None:
        voice: Optional[discord.VoiceClient] = await bot.join_vc(ctx)
        if voice and (voice.is_playing() or voice.is_paused()):
            voice.stop()
            bot.queue.clear()
            bot.running_queue = False
            gc.collect()
            embed = discord.Embed(
                title="⏹️ Stopped",
                description="Playback stopped and queue cleared.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Nothing is currently playing!")

    @bot.hybrid_command(name="skip", description="Skips the current video")
    async def skip(ctx: commands.Context) -> None:
        voice: Optional[discord.VoiceClient] = await bot.join_vc(ctx)
        if voice and (voice.is_playing() or voice.is_paused()):
            voice.stop()
            embed = discord.Embed(
                title="⏭️ Skipped",
                description="Moving to next track...",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Nothing is currently playing!")

    @bot.hybrid_command(name="queue", description="Shows the current queue")
    async def queue_cmd(ctx: commands.Context) -> None:
        if bot.queue:
            embed = discord.Embed(
                title="📜 Queue",
                color=discord.Color.blue()
            )
            
            queue_list = '\n'.join([f"`{i+1}.` {video.get('title', 'Unknown')[:60]}" for i, video in enumerate(list(bot.queue)[:10])])
            embed.description = queue_list
            
            if len(bot.queue) > 10:
                embed.set_footer(text=f"... and {len(bot.queue) - 10} more songs")
            else:
                embed.set_footer(text=f"Total: {len(bot.queue)} songs")
            
            await ctx.send(embed=embed)
        else:
            await ctx.send("📭 The queue is empty!")
    
    @bot.hybrid_command(name="pause", description="Pauses the current video")
    async def pause(ctx: commands.Context) -> None:
        voice: Optional[discord.VoiceClient] = await bot.join_vc(ctx)
        if voice and voice.is_playing():
            voice.pause()
            await ctx.send("⏸️ Paused the music.")
        else:
            await ctx.send("❌ Nothing is currently playing!")
    
    @bot.hybrid_command(name="resume", description="Resumes the paused video")
    async def resume(ctx: commands.Context) -> None:
        voice: Optional[discord.VoiceClient] = await bot.join_vc(ctx)
        if voice and voice.is_paused():
            voice.resume()
            embed = discord.Embed(
                title="▶️ Resumed",
                description="Playback resumed.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Nothing is currently paused!")
    
    @bot.hybrid_command(name="clear", description="Clears the queue without stopping current song")
    async def clear_queue(ctx: commands.Context) -> None:
        if bot.queue:
            cleared_count = len(bot.queue)
            bot.queue.clear()
            gc.collect()
            embed = discord.Embed(
                title="🗑️ Queue Cleared",
                description=f"Removed {cleared_count} songs from the queue.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("📭 The queue is already empty!")
    
    @bot.hybrid_command(name="nowplaying", description="Shows the currently playing song")
    async def nowplaying(ctx: commands.Context) -> None:
        voice: Optional[discord.VoiceClient] = await bot.join_vc(ctx)
        if voice and voice.is_playing():
            await ctx.send("ℹ️ Check the last 'Now Playing' message above!")
        else:
            await ctx.send("❌ Nothing is currently playing!")

    bot.run(token)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    load_dotenv()
    main(os.getenv('DISCORD_TOKEN'))
