from asyncio import sleep
from typing import List
from pyrogram import Client,filters
from pyrogram.types.messages_and_media.message import Message
from .. import config
from ..helpers.filters import command
from ..helpers.chat_id import get_chat_id
from Python_ARQ import ARQ
from aiohttp import ClientSession
from ..helpers.funcs import *
from ..services import queues
from ..services.downloaders import youtube
from ..services.converter import convert
from musicbot.config import DURATION_LIMIT
from ..services.callsmusic import callsmusic
from youtube_search import YoutubeSearch

# 初始化ARQ API
session = ClientSession()
arq = ARQ("https://thearq.tech",config.ARQ_API_KEY,session)

@Client.on_message(command("yt") & ~filters.edited)
async def y_song(_,message: Message):
    query = message.text.split(None, 1)
    chat_id = get_chat_id(message.chat)
    if len(query) == 1:
        m = await message.reply_text("请使用 '/s 歌曲名' 来搜索歌曲")
        await sleep(5)
        await m.delete()
        await message.delete()
        return
    query = query[1]
    if message.sender_chat:
        message.from_user = message.sender_chat
        message.from_user.first_name = message.sender_chat.username
    m = await message.reply_text(f"在油管上疯狂搜索 `{query}` 中")
    res = await arq.youtube(query)
    if not res.ok:
        await m.edit("嘛都木有找到... 要不考虑再试试别的？...")
        await sleep(5)
        await m.delete()
        await message.delete()
        return
    results= res.result
    await youtube_proc(results,message,m)

async def youtube_proc(results:List,message: Message,m: Message):
    chat_id = get_chat_id(message.chat)
    slink= f"https://youtube.com{results[0]['url_suffix']}"
    title = results[0]["title"]
    singers = results[0]["channel"]
    thumbnail = results[0]["thumbnails"][0]
    sduration = results[0]["duration"]
    duration= time_to_seconds(sduration)
    views = results[0]["views"]
    if int(duration/60)>=DURATION_LIMIT: #duration limit
            await m.edit(f"兄弟，实在太太太长了，已经超过了{DURATION_LIMIT}分钟鸟~")
            await sleep(5)
            await m.delete()
            await message.delete()
            return
    await m.delete()
    m = await message.reply_photo(thumbnail,caption=f"{title} {sduration} 小水管尽力下载中...")            
    file_path = await convert(youtube.download(slink))
    position = await queues.put(
        chat_id,slink=slink,
        title=title,singers=singers,
        thumbnail=thumbnail,sduration=sduration,
        views=views,file=file_path,
        user=message.from_user)
    if chat_id in callsmusic.active_chats:
        await m.edit_caption(f"{title} {sduration} 成功加入播放队列... 共有 {position} 首待播")
    else:
        await m.edit_caption(f"{title} {sduration} 开始播放")
        await callsmusic.set_stream(chat_id,file_path)
    # 等待5秒把搜索和搜索结果都清除
    await sleep(5)
    await m.delete()
    await message.delete()


@Client.on_message(command("y") & ~filters.edited)
async def yt_song(_,message: Message):
    if len(message.command) == 1:
        m = await message.reply_text("请使用 '/y 歌曲名' 来搜索歌曲")
        await sleep(5)
        await m.delete()
        await message.delete()
        return
    query = message.text.split(None, 1)[1]
    m = await message.reply_text(f"在油管上疯狂搜索 `{query}` 中")
    results = YoutubeSearch(query, max_results=1).to_dict()
    await youtube_proc(results,message,m)
