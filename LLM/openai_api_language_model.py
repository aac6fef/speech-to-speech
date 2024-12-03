import logging
import time
from datetime import datetime
import asyncio

from nltk import sent_tokenize
from rich.console import Console
from openai import OpenAI
from fastapi import WebSocket

from baseHandler import BaseHandler
from LLM.chat import Chat
from LLM.api_handler import APIHandler

logger = logging.getLogger(__name__)

console = Console()

WHISPER_LANGUAGE_TO_LLM_LANGUAGE = {
    "en": "english",
    "fr": "french",
    "es": "spanish",
    "zh": "chinese",
    "ja": "japanese",
    "ko": "korean",
}

class OpenApiModelHandler(BaseHandler):
    """
    Handles the language model part.
    """
    def setup(
        self,
        model_name="deepseek-chat",
        device="cuda",
        gen_kwargs={},
        base_url =None,
        api_key=None,
        stream=False,
        user_role="user",
        chat_size=1,
        init_chat_role="system",
        init_chat_prompt="You are a helpful AI assistant.",
        api_port=5000
    ):
        self.memory = {"memory":"","chats":""}
        self.init_chat_prompt = init_chat_prompt
        self.model_name = model_name
        self.stream = stream
        self.chat = Chat(chat_size)
        if init_chat_role:
            if not init_chat_prompt:
                raise ValueError(
                    "An initial promt needs to be specified when setting init_chat_role."
                )
            self.chat.init_chat({"role": init_chat_role, "content": init_chat_prompt})
        self.user_role = user_role
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.warmup()
        self.api_handler = APIHandler(port=api_port)
        self.api_handler.set_model_handler(self)
        self.api_handler.start()
        self.active_connections = set()  # 存储活跃的WebSocket连接

    def warmup(self):
        logger.info(f"Warming up {self.__class__.__name__}")
        start = time.time()
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.init_chat_prompt},
                {"role": "user", "content": "Hello"},
            ],
            stream=self.stream
        )
        end = time.time()
        logger.info(
            f"{self.__class__.__name__}:  warmed up! time: {(end - start):.3f} s"
        )

    def generate_memory(self):
        chat_content = self.memory["chats"]
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "这是你之前和用户的对话,请总结这些对话,以便保存下来成为你的记忆"},
                {"role": "user", "content": chat_content},
            ],
            stream=False
        )
        summary = response.choices[0].message.content.strip()
        return summary

    def compress_memory(self):
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "这是你的记忆内容,请总结这些内容,以便保存记忆"},
                {"role": "user", "content": self.memory["memory"]},
            ],
            stream=False
        )
        compressed_memory = response.choices[0].message.content.strip()
        return compressed_memory

    async def connect_websocket(self, websocket: WebSocket):
        """处理新的WebSocket连接"""
        await websocket.accept()
        self.active_connections.add(websocket)
        
    def disconnect_websocket(self, websocket: WebSocket):
        """处理WebSocket断开连接"""
        self.active_connections.remove(websocket)
        
    async def broadcast_message(self, message: str):
        """向所有连接的客户端广播消息"""
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                self.active_connections.remove(connection)

    def process(self, prompt):
        logger.debug("call api language model...")
        
        # 记录prompt
        self.api_handler.record_prompt(prompt)
        
        if(len(self.memory["chats"])>1000):
            logger.info("Memorizing Chats")
            self.memory["memory"] = self.generate_memory()
            self.memory["chats"] = ""
            
        # 更新memory状态
        self.api_handler.update_memory(self.memory["memory"])
        
        self.chat.append({"role": self.user_role, "content": prompt})
        language_code = None
        if isinstance(prompt, tuple):
            prompt, language_code =  prompt
            if language_code[-5:] == "-auto":
                language_code = language_code[:-5]
        prompt_to_send = f"##你的记忆\n\n{ self.memory['memory'] }\n##之前的对话\n\n{ self.memory['chats'] }\n##你现在需要回答的问题(用{WHISPER_LANGUAGE_TO_LLM_LANGUAGE[language_code]}回答.)\n\n{prompt}"
        self.memory["chats"] += f"USER:{prompt}\n"
        logger.info(f"Current prompt:{prompt_to_send}")
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.init_chat_prompt},
                {"role": self.user_role, "content": prompt_to_send}
            ],
            stream=self.stream
        )

        if self.stream:
            generated_text, printable_text = "", ""
            start_time = datetime.now()
            for chunk in response:
                new_text = chunk.choices[0].delta.content or ""
                if new_text:  # 只要有新内容就立即发送
                    self.api_handler.broadcast_ws_message(new_text)
                generated_text += new_text
                printable_text += new_text
                sentences = sent_tokenize(printable_text)
                if len(sentences) > 1:
                    yield sentences[0], language_code
                    printable_text = new_text
            end_time = datetime.now()
            self.api_handler.record_response(generated_text, start_time, end_time)
            self.chat.append({"role": "assistant", "content": generated_text})
            # don't forget last sentence
            self.memory["chats"] += f"YOU:{generated_text}\n"
            yield printable_text, language_code
        else:
            start_time = datetime.now()
            generated_text = response.choices[0].message.content
            end_time = datetime.now()
            self.api_handler.record_response(generated_text, start_time, end_time)
            self.chat.append({"role": "assistant", "content": generated_text})
            self.memory["chats"] += f"YOU:{generated_text}\n"
            yield generated_text, language_code

