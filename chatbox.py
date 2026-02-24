import streamlit as st
from openai import OpenAI
import re # Thư viện xử lý chuỗi

# 1. CẤU HÌNH API

API_KEY = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=API_KEY)

st.set_page_config(page_title="AI THCS Tăng Bạt Hổ", layout="wide")

# CSS tối giản, tập trung vào hiển thị
st.markdown("""
    <style>
    .user-box { background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin: 10px 0; }
    .ai-box { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #ddd; margin: 10px 0; }
    </style>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "assistant_id" not in st.session_state:
    st.session_state["assistant_id"] = None

# HÀM XỬ LÝ HIỂN THỊ (Sửa lỗi ảnh và dọn dẹp rác hệ thống)
def smart_display(text):
    # 1. Dọn dẹp các mã trích dẫn lỗi của OpenAI (ví dụ: 【4:0†...】)
    clean_text = re.sub(r'【.*?】', '', text)
    
    # 2. Tìm từ khóa ảnh mà AI tạo ra (Ví dụ: IMAGE_KEYWORD: robot)
    keyword_match = re.search(r'IMAGE_KEYWORD:\s*(\w+)', clean_text)
    
    # Hiển thị văn bản sạch trước (loại bỏ dòng IMAGE_KEYWORD)
    final_text = clean_text.split("IMAGE_KEYWORD:")[0]
    st.markdown(final_text)
    
    # 3. Nếu tìm thấy từ khóa, tự tạo ảnh bằng code Python để đảm bảo không bao giờ lỗi link
    if keyword_match:
        keyword = keyword_match.group(1)
        # Sử dụng link trực tiếp từ server ảnh
        img_url = f"https://image.pollinations.ai/prompt/{keyword}?width=800&height=500&nologo=true"
        st.image(img_url, caption=f"Hình ảnh minh họa: {keyword}")

st.title("🏫 Hệ Thống Trợ Lý Học Tập")

# 2. SIDEBAR
with st.sidebar:
    st.header("📂 Giáo viên")
    uploaded_file = st.file_uploader("Tải tài liệu", type=['pdf', 'txt', 'docx'])
    
    if uploaded_file and st.session_state["assistant_id"] is None:
        with st.spinner("Đang nạp tri thức..."):
            file_obj = client.files.create(file=uploaded_file, purpose='assistants')
            v_store = client.beta.vector_stores.create(name="SchoolData", file_ids=[file_obj.id])
            
            # CHỈ THỊ CỰC KỲ ĐƠN GIẢN ĐỂ AI KHÔNG LÀM SAI
            instruction_prompt = """
            Bạn là AI hỗ trợ học tập. 
            Khi trả lời:
            1. Trả lời ngắn gọn, dễ hiểu dựa trên tài liệu hoặc kiến thức của bạn.
            2. KHÔNG được dùng các ký hiệu lạ như 【...】.
            3. CUỐI CÂU LUÔN VIẾT dòng chữ sau: IMAGE_KEYWORD: [từ khóa tiếng Anh về chủ đề đang nói]
            Ví dụ: IMAGE_KEYWORD: robot
            """
            
            assist = client.beta.assistants.create(
                name="Assistant",
                instructions=instruction_prompt,
                tools=[{"type": "file_search"}],
                tool_resources={"file_search": {"vector_store_ids": [v_store.id]}},
                model="gpt-4o"
            )
            st.session_state["assistant_id"] = assist.id
            st.success("Sẵn sàng!")

    if st.button("Xóa hội thoại"):
        st.session_state["messages"] = []
        st.experimental_rerun()

# 3. HIỂN THỊ CHAT
for m in st.session_state["messages"]:
    if m["role"] == "user":
        st.markdown(f'<div class="user-box"><b>🧑‍🎓 Học sinh:</b><br>{m["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown('**🤖 AI Trả lời:**')
        with st.container():
            smart_display(m["content"])
        st.markdown('---')

# 4. NHẬP CÂU HỎI
user_input = st.text_input("Nhập câu hỏi của em:", key="input_text")
if st.button("Gửi câu hỏi"):
    if user_input:
        st.session_state["messages"].append({"role": "user", "content": user_input})
        
        if st.session_state["assistant_id"]:
            with st.spinner("Đang tìm câu trả lời..."):
                thread = client.beta.threads.create(messages=[{"role": "user", "content": user_input}])
                run = client.beta.threads.runs.create_and_poll(
                    thread_id=thread.id, 
                    assistant_id=st.session_state["assistant_id"]
                )
                if run.status == 'completed':
                    messages = client.beta.threads.messages.list(thread_id=thread.id)
                    ans = messages.data[0].content[0].text.value
                    st.session_state["messages"].append({"role": "assistant", "content": ans})
                    st.experimental_rerun()
