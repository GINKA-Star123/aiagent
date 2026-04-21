from __future__ import annotations

import time
import aiohttp
import pygame
import queue
import threading
import uuid
import re
import requests
import logging

pygame.mixer.init()

def normalize_text(text:str) -> str:
    """标准化LLM生成的文本以此便于后续的语音生成

    Args:
        LLM生成的文本

    Returns:
        str:标准化后的文本
    """

    text = re.sub(r'（.*?）', '', text)
    text = re.sub(r'\(.*?\)', '', text)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\{.*?\}', '', text)
    # 去除星号内容
    text = re.sub(r'\*.*?\*', '', text)
    return text.strip()


def split_text_streaming(text:str,max_length:int =20) -> list[str]:
    """切割文本实现类流式生成，以此达到类似实时语音的效果    

    Args:
        text:经过标准化的文本
        max_length:每个分句的最大长度


    """
    strong_punc = "。！？!?"
    weak_punc = "，,；;"

    segments = []
    buf = ""

    for ch in text:
        buf += ch

        # 强标点，直接切
        if ch in strong_punc:
            segments.append(buf.strip())
            buf = ""
            continue

        # 弱标点 + 长度接近上限
        if ch in weak_punc and len(buf) >= max_length * 0.7:
            segments.append(buf.strip())
            buf = ""

        # 兜底：过长强制切（但尽量少发生）
        if len(buf) >= max_length:
            segments.append(buf.strip())
            buf = ""

    if buf.strip():
        segments.append(buf.strip())

    return segments


class TTSTools:
    def __init__(self) ->None:
        self.url=" http://localhost:8000/synthesize"
        self.audio_queue = queue.Queue()
        self.segments :list[str] = []
    
    def normalize_text(self,text:str) -> str:
        """标准化LLM生成的文本以此便于后续的语音生成

        Args:
            LLM生成的文本

        Returns:
            str:标准化后的文本
        """

        text = re.sub(r'（.*?）', '', text)
        text = re.sub(r'\(.*?\)', '', text)
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'\{.*?\}', '', text)
        # 去除星号内容
        text = re.sub(r'\*.*?\*', '', text)
        return text.strip()
    
    def split_text_streaming(self,segments:list[str],text:str,max_length:int =20) -> list[str]:
        """切割文本实现类流式生成，以此达到类似实时语音的效果    

        Args:
            text:经过标准化的文本
            max_length:每个分句的最大长度


        """
        strong_punc = "。！？!?"
        weak_punc = "，,；;"

        buf = ""

        for ch in text:
            buf += ch

            # 强标点，直接切
            if ch in strong_punc:
                segments.append(buf.strip())
                buf = ""
                continue

            # 弱标点 + 长度接近上限
            if ch in weak_punc and len(buf) >= max_length * 0.7:
                segments.append(buf.strip())
                buf = ""

            # 兜底：过长强制切（但尽量少发生）
            if len(buf) >= max_length:
                segments.append(buf.strip())
                buf = ""

        if buf.strip():
            segments.append(buf.strip())

        return segments

    async def tts_segment(self,text:str):
        """
        将文本转换为语音

        Args:
            text:经过标准化的文本
        """
        text = self.normalize_text(text)
        payload = {
            "text":text,
            "ref_audio":"refaudio.wav",
            "emo_alpha":0.6,
            "use_emo_text":True,
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.url, json=payload) as r:
                    if r.status != 200:
                        print("TTS 请求失败", await r.text())
                        return
                
                    data = await r.read()

                    # 避免同名覆盖
                    path = f"{uuid.uuid4().hex}.wav"
                    with open(path, "wb") as f:
                        f.write(data)
                    
                    sound = pygame.mixer.Sound(path)
                    duration = sound.get_length()
                    return path, duration
            except Exception as e:
                print(e,"请求在TTS中失败")

    async def speak_streaming(self,text):
        """
        实现类流式生成，以此达到类似实时语音的效果

        args:
            text:经过标准化的文本
        """
        text =self.normalize_text(text)
        segments = split_text_streaming(text)

        for seg in segments:
            result = await tts_segment(seg) # type: ignore
            if result:  # 检查是否为None
                path, duration = result
                self.audio_queue.put((path, seg))
            else:
                print(f"⚠️ TTS 生成失败: {seg}")
            
    def player_worker(self):
        """
        播放语音
        """
        while True:
            path = self.audio_queue.get()
            if path is None:
                break
            
            audio_path , subtitle = path    
            data = {
                "type": "speak",
                "speech_path": rf"F:\AIYZL\{audio_path}" # 修改为你的语音音频路径
            }
            print(audio_path)
            res = requests.post(url=self.url,json =data)
            logging.info(f"正在播放: {subtitle}")
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()
            
            #等待播放完
            while pygame.mixer.music.get_busy():
                time.sleep(0.01)
            time.sleep(0.3)  # 播放间隔