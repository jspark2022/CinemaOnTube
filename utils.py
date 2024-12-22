

#--------------------------------------

import os
import re
import tempfile
from yt_dlp import YoutubeDL
from whisper import load_model
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
from googleapiclient.discovery import build
from tmdbv3api import TMDb, Movie
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

# API Keys 설정
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# OpenAI API Key 설정
openai.api_key = OPENAI_API_KEY

# TMDb 설정
tmdb = TMDb()
tmdb.api_key = TMDB_API_KEY
tmdb.language = "ko-KR" 
movie = Movie()

# Whisper 모델 초기화
whisper_model = load_model("tiny")


def check_transcript_availability(video_id):
    try:
        YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'en'])
        return True
    except (NoTranscriptFound, TranscriptsDisabled):
        return False
    except Exception as e:
        print(f"자막 확인 오류: {e}")
        return False


def get_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'en'])
        return " ".join([item['text'] for item in transcript])
    except Exception as e:
        print(f"자막 가져오기 오류: {e}")
        return None


def get_video_description(video_id):
    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        request = youtube.videos().list(part="snippet", id=video_id)
        response = request.execute()
        return response["items"][0]["snippet"].get("description", "설명 없음")
    except Exception as e:
        print(f"비디오 설명 가져오기 오류: {e}")
        return None


def download_audio(youtube_url):
    try:
        temp_dir = tempfile.mkdtemp()
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(temp_dir, "audio.%(ext)s"),
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}],
        }
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
        return os.path.join(temp_dir, "audio.wav")
    except Exception as e:
        raise RuntimeError(f"오디오 다운로드 오류: {e}")


def transcribe_audio(audio_path):
    try:
        result = whisper_model.transcribe(audio_path)
        return result["text"]
    except Exception as e:
        raise RuntimeError(f"Whisper 변환 오류: {e}")


def summarize_text_in_korean(input_text):
    try:
        system_role = '''당신은 영화 리뷰를 요약하는 AI 어시스턴트입니다.'''
        user_message = f"리뷰 텍스트: {input_text}"

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": user_message}
            ],
            max_tokens=300,
            temperature=0.5,
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        raise RuntimeError(f"요약 오류: {e}")


def infer_movie_title(description=None, transcript=None, audio_text=None):
    texts = [description, transcript, audio_text]
    combined_text = " ".join(filter(None, texts))
    if not combined_text:
        return None

    try:
        system_role = "다음 텍스트에서 영화 제목을 추론하세요."
        user_message = f"텍스트: {combined_text}"

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": user_message}
            ],
            max_tokens=50,
            temperature=0.5,
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        raise RuntimeError(f"영화 제목 추론 오류: {e}")


# 


def get_movie_info(title):
    try:
        # TMDb API에서 영화 검색
        search_results = movie.search(title)
        
        # 검색 결과 유효성 확인
        if not search_results:
            return {"error": "TMDb 검색 결과가 없습니다."}
        
        result = search_results[0]
        
        # 결과 데이터 유효성 확인 및 포스터 URL 생성
        poster_path = getattr(result, 'poster_path', None)
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
        
        # 결과 데이터 반환
        return {
            "제목": getattr(result, 'title', "제목 없음") if hasattr(result, 'title') else "제목 없음",
            "개요": getattr(result, 'overview', "개요 없음") if hasattr(result, 'overview') else "개요 없음",
            "개봉일": getattr(result, 'release_date', "개봉일 없음") if hasattr(result, 'release_date') else "개봉일 없음",
            "평점": getattr(result, 'vote_average', "평점 없음") if hasattr(result, 'vote_average') else "평점 없음",
            "포스터 URL": poster_url
        }
    except Exception as e:
        # 상세 오류 메시지 반환
        raise RuntimeError(f"TMDb 검색 오류: {e}")

