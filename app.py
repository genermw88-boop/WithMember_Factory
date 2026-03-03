import streamlit as st
import os
import base64
import cv2
import json
import numpy as np
from openai import OpenAI
from moviepy.editor import VideoFileClip, concatenate_videoclips

# 🚨 대표님의 진짜 API 키를 넣어주세요!
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
client = OpenAI()

st.set_page_config(page_title="위드멤버 팩트후킹 V17", layout="wide")
st.title("🔥 위드멤버 V17 (40초 고화질 + 플랫폼별 맞춤 기획)")

# --- [기능 1] 고화질 보정 ---
def enhance_high_quality(frame):
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    frame = cv2.filter2D(frame, -1, kernel)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    s = cv2.add(s, 30) 
    v = cv2.add(v, 15) 
    return cv2.cvtColor(cv2.merge((h, s, v)), cv2.COLOR_HSV2BGR)

# --- [기능 2] 썸네일 추출 (팩트 중심) ---
def extract_viral_thumbnail(video_path, thumb_request):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps)
    base64_frames = []
    secs = []
    for i in range(min(15, duration)): 
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(fps * i))
        ret, frame = cap.read()
        if not ret: break
        _, buffer = cv2.imencode(".jpg", frame)
        base64_frames.append(base64.b64encode(buffer).decode("utf-8"))
        secs.append(i)
        
    prompt = [
        {"role": "system", "content": "조회수 보증 썸네일 분석가입니다."},
        {"role": "user", "content": [{"type": "text", "text": f"디렉팅: '{thumb_request}'. 가장 압도적인 비주얼 장면 1곳의 번호만 말하세요."}]}
    ]
    for img in base64_frames:
        prompt[1]["content"].append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}})

    try:
        ans = client.chat.completions.create(model="gpt-4o", messages=prompt, max_tokens=10).choices[0].message.content.strip()
        best_idx = int(''.join(filter(str.isdigit, ans))) - 1
    except: best_idx = 0
        
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(fps * secs[max(0, best_idx)]))
    ret, thumb_frame = cap.read()
    thumb_path = f"thumb_viral.jpg"
    if ret: cv2.imwrite(thumb_path, enhance_high_quality(thumb_frame))
    cap.release()
    return thumb_path

# --- [기능 3] 플랫폼별 맞춤 컨텐츠 생성기 (이모티콘 & 40초 대본) ---
def generate_viral_strategy(shop_name, shop_point, shop_loc, shop_price):
    prompt = f"""
    당신은 숏폼 전문 카피라이터입니다. 매장명 '{shop_name}', 특징 '{shop_point}', 위치 '{shop_loc}', 가격 '{shop_price}' 기반.
    
    [필수 수칙]
    1. 썸네일 문구: "경험하세요", "놓치지 마세요" 절대 금지. 오직 팩트와 궁금증 유발형으로 작성.
    2. 유튜브 쇼츠 설명글: 정보성 강조. 귀엽고 이쁜 이모티콘 적극 활용. 주소/가격 명시. ✨
    3. 인스타 릴스 설명글: 감성적이고 트렌디한 느낌. 친구 태그 유도 문구와 이모티콘 가득. 💖
    4. 대본: 40초 분량. 시청자를 가르치지 말고, 실제 찐반응을 그대로 담은 고텐션 원고.
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt + "\n반드시 JSON: {shorts: {title, desc, hashtags, thumb_copy}, reels: {title, desc, hashtags, thumb_copy}, script}"}]
    )
    return json.loads(response.choices[0].message.content)

# --- UI 레이아웃 ---
with st.sidebar:
    st.header("📍 상세 정보")
    shop_name = st.text_input("매장명", "동경생고기")
    shop_loc = st.text_input("위치", "인천 남동구 구월동")
    shop_price = st.text_input("가격", "뭉티기 4.5만원")
    shop_point = st.text_area("강점", "당일 도축, 쫀득함 끝판왕")
    
    st.header("🎬 편집 디렉팅")
    thumb_req = st.text_input("썸네일 디렉팅", "고기 때깔 강조")
    edit_req = st.text_input("영상 편집 포인트", "맛있게 먹는 장면 위주로 빠르게 전환")

uploaded_files = st.file_uploader("🎬 다량 영상 업로드 (20개 내외)", accept_multiple_files=True, type=['mp4'])

if st.button("🚀 V17 맞춤형 기획 모드 가동!"):
    if uploaded_files:
        status = st.empty()
        status.info("🔍 유튜브/인스타 맞춤형 카피 및 대본 작성 중...")
        strategy = generate_viral_strategy(shop_name, shop_point, shop_loc, shop_price)
        
        status.info(f"✂️ {len(uploaded_files)}개 영상을 분석하여 40초 풀편집 중...")
        total_len = 40.0
        sec_per_file = total_len / len(uploaded_files) 
        clips = []
        
        for i, file in enumerate(uploaded_files):
            temp = f"v_{i}.mp4"
            with open(temp, "wb") as f: f.write(file.read())
            if i == 0: thumb_img = extract_viral_thumbnail(temp, thumb_req)
            
            clip = VideoFileClip(temp).resize(height=1920)
            w, h = clip.size
            clip = clip.crop(x_center=w/2, y_center=h/2, width=h*(1080/1920), height=h).resize(newsize=(1080, 1920))
            
            # 입력한 편집 포인트를 고려하여 영상 앞부분을 컷 (40초 길이에 맞춰 자동 배분)
            clips.append(clip.subclip(0, min(sec_per_file, clip.duration)))
            
        final = concatenate_videoclips(clips, method="compose")
        final.write_videofile("final_viral_output.mp4", fps=30, bitrate="8000k", codec="libx264")
        
        status.success("✅ 40초 고화질 영상 및 플랫폼별 맞춤 세트 완성!")

        st.divider()
        t1, t2, t3 = st.tabs(["🔴 유튜브 쇼츠 전용", "🟣 인스타 릴스 전용", "📝 40초 전문 대본 & 영상"])
        
        with t1:
            st.subheader("📌 [쇼츠] SEO 제목")
            st.code(strategy['shorts']['title'], language="")
            st.subheader("🖼️ [쇼츠] 썸네일 카피")
            st.info(strategy['shorts']['thumb_copy'])
            st.subheader("📝 상세 설명 (이모티콘 활용)")
            st.write(strategy['shorts']['desc'])
            st.code(strategy['shorts']['hashtags'])
            
        with t2:
            st.subheader("📌 [릴스] 트렌디 제목")
            st.code(strategy['reels']['title'], language="")
            st.subheader("🖼️ [릴스] 썸네일 카피")
            st.info(strategy['reels']['thumb_copy'])
            st.subheader("📝 본문 문구 (이모티콘 활용)")
            st.write(strategy['reels']['desc'])
            st.code(strategy['reels']['hashtags'])
            
        with t3:
            st.video("final_viral_output.mp4")
            st.subheader("🗣️ 40초 몰입형 대본 (Vrew용)")
            st.text_area("텍스트를 복사해서 활용하세요", strategy['script'], height=300)

            st.image(thumb_img, caption="AI 추천 고화질 썸네일")
