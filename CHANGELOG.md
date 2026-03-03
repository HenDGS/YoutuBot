# Changelog

All notable changes to YoutuBot will be documented in this file.

## [v2.0.0]

### New Features
- **Interactive Music Controls**: New UI buttons for Pause, Resume, Skip, Stop, and Queue displayed directly in Discord messages alongside the Now Playing embed
- **Playlist Support**: Full support for YouTube playlists with parallel batch processing (3 at a time) and real-time progress updates
- **New Commands**:
  - `/pause` - Pause the current song
  - `/resume` - Resume paused playback
  - `/clear` - Clear the queue without stopping the current song
  - `/nowplaying` - Show info about the currently playing song
- **Now Playing Embed**: Rich embed with video thumbnail, channel name, and formatted duration when a song starts
- **Added to Queue Embed**: Embed confirmation with position and duration when adding to an existing queue

### Improvements
- **Video Caching**: LRU cache (up to 50 entries) for video metadata to reduce redundant yt-dlp API calls
- **Memory Optimization**: Automatic cleanup of large video metadata fields (formats, thumbnails, captions, subtitles) after playback starts to reduce memory footprint
- **Better Error Handling**: Specific error messages for age-restricted, unavailable, and private videos across all commands
- **Playlist Progress Tracking**: Real-time status updates every 15 videos when loading large playlists, including counts of skipped/age-restricted videos
- **Optimized Voice Client**: Improved FFmpeg reconnect options and better state management for paused/playing transitions
- **Garbage Collection**: Explicit `gc.collect()` calls after stop and clear operations to free memory promptly
- **Minimal Intents**: Disabled `members` and `presences` intents for better performance and reduced permissions required

### Bug Fixes
- Fixed issue where a paused voice client would not stop properly before starting new playback
- Fixed queue display truncating titles at 60 characters and showing up to 10 items with overflow count
- Improved handling of playlists with no valid entries

## [1.0] - 2024-06-07

### Initial Release
- `/play` - Play a video from URL or search query, joins voice channel automatically
- `/stop` - Stop playback and clear the queue
- `/skip` - Skip the current video
- `/queue` - Display the current queue
- Basic yt-dlp integration for YouTube and other supported sites
- Queue management with automatic playback of next item
