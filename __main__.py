from youtubesearchpython import VideosSearch
from pytube import YouTube

import os
import dotenv
import discord
import asyncio
from mutagen.mp3 import MP3

CHANNEL_ID = 1015465255901601823
MUSIC_PATH = 'music/music{}.mp3'
UPDATE_DELAY = 1

class Rapid(discord.Client):
    def search_video(self, keyword):
        videos = VideosSearch(keyword, limit=1)
        video = videos.result()['result'][0]

        video_data = {
            'title': video['title'],
            'duration': video['duration'],
            'thumbnail_url': video['thumbnails'][0]['url'],
            'video_url': video['link'],
            'channel_name': video['channel']['name'],
        }

        return video_data

    def download_audio(self, video_data):
        yt = YouTube(video_data['video_url'])
        video = yt.streams.filter(only_audio=True).first()
        out_file = video.download(output_path=".")

        self.song_number += 1
        music_path = MUSIC_PATH.format(self.song_number)
        if os.path.exists(music_path):
            os.remove(music_path)

        base, ext = os.path.splitext(out_file)
        os.rename(out_file, music_path)

        return music_path

    def create_embed(self, info={}, fields={}):
        embed = discord.Embed(
            title = info.get('title') or '',
            description = info.get('description') or '',
            colour = info.get('color') or discord.Color.blue(),
            url = info.get('url') or f'',
        )

        for name, value in fields.items():
            embed.add_field(name=name, value=value, inline=info.get('inline') or False)

        if info.get('author'):
            embed.set_author(name=info.author.name, url=info.author.mention, icon_url=info.author.avatar_url)
        if info.get('footer'):
            embed.set_footer(text=info.get('footer'))
        if info.get('image'):
            embed.set_image(url=info.url)
        if info.get('thumbnail'):
            embed.set_thumbnail(url=info.get('thumbnail'))
    
        return embed

    async def execute_help(self, message):
        fields = {}
        for command_name, command_info in self.commands.items():
            fields[command_name] = command_info['description']

        await message.reply(embed=self.create_embed({
            'title': 'Commands',
            'inline': True,
        }, fields))

    async def execute_join(self, message):
        user_voice = message.author.voice
        if not user_voice:
            await message.reply(embed=self.create_embed({
                'title': 'You are not in a VC',
                'color': discord.Color.red()
            }))

            return

        user_voice_channel = user_voice.channel
        if not user_voice_channel:
            await message.reply(embed=self.create_embed({
                'title': 'You are not in a VC',
                'color': discord.Color.red()
            }))

            return

        if self.voice_client and self.voice_client.channel == user_voice_channel:
            await message.reply(embed=self.create_embed({
                'title': 'Already connected',
                'color': discord.Color.red()
            }))

            return

        self.voice_client = await user_voice_channel.connect()
        await message.reply(embed=self.create_embed({
            'title': f'Joined VC {user_voice_channel.name}',
            'color': discord.Color.green()
        }))

        while True:
            await asyncio.sleep(1)

            if not self.voice_client or not self.voice_client.channel:
                return

            if len(self.music_queue) == 0:
                continue

            next_song = self.music_queue[0]
            if next_song:
                song_name = next_song['video_data']['title']
                song_path = next_song['path']

                self.voice_client.stop()
                self.voice_client.play(discord.FFmpegPCMAudio(song_path))

                await message.reply(embed=self.create_embed({
                    'title': f'Playing {song_name}',
                    'color': discord.Color.green(),
                    'thumbnail': next_song['video_data']['thumbnail_url'],
                    'inline': True,
                }, {
                    'Channel': next_song['video_data']['channel_name'],
                    'Duration': next_song['video_data']['duration'],
                }))

                while True:
                    if not self.voice_client.is_playing:
                        break

                    await asyncio.sleep(1)

                self.music_queue.pop(0)

    async def execute_leave(self, message):
        if not self.voice_client:
            await message.reply(embed=self.create_embed({
                'title': 'Not in a VC',
                'color': discord.Color.red()
            }))

            return

        await self.voice_client.disconnect()
        self.voice_client = None

        await message.reply(embed=self.create_embed({
            'title': 'Left the VC',
            'color': discord.Color.green()
        }))

    async def execute_play(self, message):
        keyword = message.content
        video_data = self.search_video(keyword)
        if not video_data:
            await message.reply(embed=self.create_embed({
                'title': f'Could not find song {keyword}',
                'color': discord.Color.red()
            }))

            return

        music_title = video_data['title']
        await message.reply(embed=self.create_embed({
            'title': f'Queued {music_title}',
            'color': discord.Color.green(),
            'thumbnail': video_data['thumbnail_url'],
            'inline': True,
        }, {
            'Channel': video_data['channel_name'],
            'Duration': video_data['duration'],
        }))

        music_path = self.download_audio(video_data)
        self.music_queue.append({
            'path': music_path,
            'video_data': video_data,
        })

        if not self.voice_client:
            await self.execute_join(message)

    async def execute_pause(self, message):
        if not self.voice_client:
            await message.reply(embed=self.create_embed({
                'title': 'Not in a VC',
                'color': discord.Color.red()
            }))

            return

        if self.voice_client.is_paused():
            await message.reply(embed=self.create_embed({
                'title': 'Already paused',
                'color': discord.Color.red()
            }))

            return

        if not self.voice_client.is_playing():
            await message.reply(embed=self.create_embed({
                'title': 'Not playing anything',
                'color': discord.Color.red()
            }))

            return

        self.voice_client.pause()

        await message.reply(embed=self.create_embed({
            'title': 'Paused',
            'color': discord.Color.green()
        }))

    async def execute_resume(self, message):
        if not self.voice_client:
            await message.reply(embed=self.create_embed({
                'title': 'Not in a VC',
                'color': discord.Color.red()
            }))

            return

        if not self.voice_client.is_paused():
            await message.reply(embed=self.create_embed({
                'title': 'Not paused',
                'color': discord.Color.red()
            }))

            return

        self.voice_client.resume()

        await message.reply(embed=self.create_embed({
            'title': 'Resumed',
            'color': discord.Color.green()
        }))

    async def execute_skip(self, message):
        if not self.voice_client:
            await message.reply(embed=self.create_embed({
                'title': 'Not in a VC',
                'color': discord.Color.red()
            }))

            return

        self.voice_client.stop()

        await message.reply(embed=self.create_embed({
            'title': f'Paused',
            'color': discord.Color.green()
        }))

    async def execute_queue(self, message):
        queue_parts = []
        for index, song in enumerate(self.music_queue):
            text = '{}. {}'.format(index + 1, song['video_data']['title'])
            queue_parts.append(text)
        
        await message.reply(embed=self.create_embed({
            'title': 'Queue'
        }, {
            'Upcoming Songs': '\n'.join(queue_parts)
        }))

    async def execute_remove(self, message):
        message_parts = message.content.split(' ')
        index = int(message_parts[1]) - 1

        music_title = self.music_queue[index]['video_data']['title']
        await message.reply(embed=self.create_embed({
            'title': f'Removed {music_title}'
        }))

        self.music_queue.pop(index)

    async def on_ready(self):
        self.music_queue = []
        self.song_number = 0
        self.voice_client = None
        self.commands = {
            'help': {'execute': self.execute_help, 'aliases': ['help', 'cmds'], 'description': 'Shows a list of commands'},
            'join': {'execute': self.execute_join, 'aliases': ['join', 'summon'], 'description': 'Joins the VC'},
            'leave': {'execute': self.execute_leave, 'aliases': ['leave'], 'description': 'Leaves the VC'},
            'play': {'execute': self.execute_play, 'aliases': [], 'description': 'Plays a song'},
            'pause': {'execute': self.execute_pause, 'aliases': ['pause', 'stop'], 'description': 'Pauses the current song'},
            'resume': {'execute': self.execute_resume, 'aliases': ['resume'], 'description': 'Resumes the paused song'},
            'skip': {'execute': self.execute_skip, 'aliases': ['skip', 'next'], 'description': 'Skips the current song'},
            'queue': {'execute': self.execute_queue, 'aliases': ['queue'], 'description': 'Shows a list of queued songs'},
            'remove': {'execute': self.execute_remove, 'aliases': ['remove'], 'description': 'Removes a song from the queue'},
        }

        print('Ready')

    async def on_message(self, message):
        if message.channel.id == CHANNEL_ID and not message.author.bot:
            for command_info in self.commands.values():
                for alias in command_info['aliases']:
                    if alias in message.content:
                        await command_info['execute'](message)
                        return

            await self.execute_play(message)

def __main__():
    intents = discord.Intents.default()
    intents.message_content = True

    dotenv.load_dotenv('.env')
    token = os.getenv('TOKEN')

    client = Rapid(intents=intents)
    client.run(token)

if __name__ == '__main__':
    __main__()
