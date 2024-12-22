

#-------------------------------------------------------
from flask import Flask, request, render_template
from utils import (
    check_transcript_availability,
    get_transcript,
    get_video_description,
    download_audio,
    transcribe_audio,
    infer_movie_title,
    get_movie_info,
    summarize_text_in_korean,
)

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        youtube_url = request.form.get("youtube_url")
        if not youtube_url:
            return render_template("index.html", error="YouTube URL을 입력하세요.")

        try:
            # Step 1: Extract YouTube video ID
            video_id = youtube_url.split("v=")[-1].split("&")[0]

            # Step 2: Extract description, transcript, or audio text
            description = get_video_description(video_id)
            transcript = get_transcript(video_id) if check_transcript_availability(video_id) else None
            audio_text = None

            if not transcript:
                audio_path = download_audio(youtube_url)
                audio_text = transcribe_audio(audio_path)

            # Step 3: Summarize review
            text_source = transcript or audio_text or description
            review_summary = summarize_text_in_korean(text_source) if text_source else None

            # Step 4: Infer movie title
            movie_title = infer_movie_title(description, transcript, audio_text)
            if not movie_title:
                return render_template("index.html", error="영화 제목을 추론할 수 없습니다.")

            # Step 5: Get movie info
            movie_info = get_movie_info(movie_title)

            # Step 6: Render results
            return render_template(
                "index.html",
                movie_info=movie_info,
                review_summary=review_summary,
                youtube_url=youtube_url,
            )

        except Exception as e:
            return render_template("index.html", error=f"처리 중 오류 발생: {e}")

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)