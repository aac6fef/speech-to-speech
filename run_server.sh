#!/usr/bin/env bash
source .venv/bin/activate
prompt=$(cat prompt.txt)
python s2s_pipeline.py \
    --tts melo\
    --llm open_api \
    --stt_model_name openai/whisper-large-v3 \
    --open_api_model_name gpt-4o \
    --open_api_api_key sk-D7i4orzHzG1VpKiU641d27B64c3c41Ff93Df9fAbAc539792 \
    --open_api_base_url "https://aihubmix.com/v1" \
    --open_api_stream True\
    --language auto \
    --open-api-init-chat-prompt "$prompt" \
    --init_chat_prompt "$prompt"\
    --recv_host 0.0.0.0 \
	--send_host 0.0.0.0 