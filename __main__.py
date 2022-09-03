from youtubesearchpython import VideosSearch
from pytube import YouTube
import os
import dotenv
import discord
import asyncio

CHANNEL_ID = 1015465255901601823
MUSIC_PATH = 'music{}.mp3'
UPDATE_DELAY = 1

class MyClient(discord.Client):
    def search_video(self, keyword):
        videos = VideosSearch(keyword, limit=1)
        video = videos.result()['result'][0]
        return video['title'], video['link']

    def download_audio(self, title, link):
        yt = YouTube(link)
        video = yt.streams.filter(only_audio=True).first()
        out_file = video.download(output_path=".")

        self.song_number += 1
        music_path = MUSIC_PATH.format(self.song_number)
        if os.path.exists(music_path):
            os.remove(music_path)

        base, ext = os.path.splitext(out_file)
        os.rename(out_file, music_path)

        return music_path

    async def on_ready(self):
        print(f'Ready...')

        self.music_queue = []
        self.song_number = 0

        while True:
            if len(self.music_queue) > 0 and len(self.voice_clients) > 0:
                voice_client = self.voice_clients[0]
                if voice_client and not voice_client.is_playing():
                    next_song = self.music_queue[0]
                    if next_song:
                        voice_client.stop()
                        voice_client.play(discord.FFmpegPCMAudio(next_song))

                        self.music_queue.pop(0)

            await asyncio.sleep(UPDATE_DELAY)

    async def on_message(self, message):
        if message.channel.id == CHANNEL_ID and not message.author.bot:
            if message.content == 'join':
                user_voice = message.author.voice
                if user_voice:
                    user_voice_channel = user_voice.channel
                    if user_voice_channel:
                        await user_voice_channel.connect()
                        await message.channel.send('joined')
            elif message.content == 'skip':
                if len(self.voice_clients) > 0:
                    voice_client = self.voice_clients[0]
                    voice_client.stop()
                    await message.channel.send('skipped')
            else: # play songs   
                keyword = message.content
                title, link = self.search_video(keyword)
                if title and link:
                    music_path = self.download_audio(title, link)
                    self.music_queue.append(music_path)
                    await message.channel.send(f'queued {title}')

def __main__():
    intents = discord.Intents.default()
    intents.message_content = True

    dotenv.load_dotenv('.env')
    token = os.getenv('TOKEN')

    client = MyClient(intents=intents)
    client.run(token)

if __name__ == '__main__':
    __main__()
