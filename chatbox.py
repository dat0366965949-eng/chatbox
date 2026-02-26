import streamlit as st
from openai import OpenAI
import openai
import re

# 1. CẤU HÌNH API
try:
    API_KEY = st.secrets["OPENAI_API_KEY"]
except:
    # Nếu chạy local mà không có secrets, thay key trực tiếp vào đây
    API_KEY = "sk-xxx"

client = OpenAI(api_key=API_KEY)

st.set_page_config(page_title="AI THCS Tăng Bạt Hổ", layout="wide")

# CSS giao diện
st.markdown("""
    <style>
    .user-box { background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin: 10px 0; border-left: 5px solid #2196F3; }
    .ai-box { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #ddd; margin: 10px 0; border-left: 5px solid #4CAF50; }
    </style>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "assistant_id" not in st.session_state:
    st.session_state["assistant_id"] = None

# HÀM HIỂN THỊ THÔNG MINH
def smart_display(text):
    # Dọn dẹp mã trích dẫn hệ thống 【...】
    clean_text = re.sub(r'【.*?】', '', text)
    # Tìm từ khóa ảnh (Cho phép dấu gạch dưới)
    keyword_match = re.search(r'IMAGE_KEYWORD:\s*([\w_]+)', clean_text)

    final_text = clean_text.split("IMAGE_KEYWORD:")[0]
    st.markdown(final_text)

    if keyword_match:
        keyword = keyword_match.group(1)
        img_url = f"https://image.pollinations.ai/prompt/{keyword}?width=800&height=500&nologo=true"
        st.image(img_url, caption=f"Hình ảnh minh họa: {keyword}")

st.title("🏫 Hệ Thống Trợ Lý Học Tập")
st.caption("Trường THCS Tăng Bạt Hổ | Hỗ trợ tài liệu & Kiến thức tổng hợp")

# 2. SIDEBAR
with st.sidebar:
    st.header("📂 Quản lý")
    uploaded_file = st.file_uploader("Tải tài liệu giảng dạy", type=['pdf', 'txt', 'docx'])

    if uploaded_file and st.session_state["assistant_id"] is None:
        with st.spinner("Đang nạp tri thức..."):
            try:
                # Tải file lên hệ thống
                file_obj = client.files.create(file=uploaded_file, purpose='assistants')

                # CHỈ THỊ AI (Ưu tiên file, nếu không có lấy kiến thức mạng)
                instruction_prompt = """
                Bạn là AI hỗ trợ học tập của trường THCS Tăng Bạt Hổ. 
                NHIỆM VỤ:
                1. ƯU TIÊN FILE: Nếu có tài liệu, tìm trong đó trước. Bắt đầu bằng "[Theo tài liệu]:".
                2. KIẾN THỨC MẠNG: Nếu tài liệu không có thông tin, hãy dùng kiến thức tổng hợp của bạn để giải đáp chi tiết. Bắt đầu bằng "[Ngoài tài liệu]:".
                3. HÌNH ẢNH: Luôn kết thúc bằng dòng 'IMAGE_KEYWORD: [từ khóa tiếng Anh]' để minh họa.
                """

                # ✅ SỬA CHỈ ĐỂ TƯƠNG THÍCH openai 2.x:
                # vector_stores nằm ở client.vector_stores (không phải client.beta.vector_stores)
                # và không create kèm file_ids; phải add file qua file_batches + poll
                v_store = client.vector_stores.create(name="SchoolData")
                client.vector_stores.file_batches.create_and_poll(
                    vector_store_id=v_store.id,
                    file_ids=[file_obj.id],
                )

                assist = client.beta.assistants.create(
                    name="Assistant",
                    instructions=instruction_prompt,
                    tools=[{"type": "file_search"}],
                    tool_resources={"file_search": {"vector_store_ids": [v_store.id]}},
                    model="gpt-4o"
                )

                st.session_state["assistant_id"] = assist.id
                st.success("Tài liệu đã sẵn sàng!")
            except Exception as e:
                st.error(f"Lỗi hệ thống: {e}")

    if st.button("Xóa hội thoại"):
        st.session_state["messages"] = []
        st.rerun()

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
# Nếu chưa nạp file, tự động tạo một Assistant "kiến thức mạng" để vẫn dùng được
if st.session_state["assistant_id"] is None:
    if st.button("Sử dụng chế độ Kiến thức mạng (Không cần file)"):
        assist = client.beta.assistants.create(
            name="General Assistant",
            instructions="Bạn là AI hỗ trợ học tập. Hãy dùng kiến thức của bạn để trả lời. Cuối câu luôn ghi IMAGE_KEYWORD: [từ khóa tiếng Anh]",
            model="gpt-4o"
        )
        st.session_state["assistant_id"] = assist.id
        st.rerun()

user_input = st.text_input("Học sinh muốn hỏi gì thầy cô nào?", key="input_text")
if st.button("Gửi câu hỏi") or (user_input and st.session_state.get('last_input') != user_input):
    if user_input:
        st.session_state["messages"].append({"role": "user", "content": user_input})

        if st.session_state["assistant_id"]:
            with st.spinner("Đang tìm câu trả lời..."):
                try:
                    thread = client.beta.threads.create(messages=[{"role": "user", "content": user_input}])
                    run = client.beta.threads.runs.create_and_poll(
                        thread_id=thread.id,
                        assistant_id=st.session_state["assistant_id"]
                    )
                    if run.status == 'completed':
                        messages = client.beta.threads.messages.list(thread_id=thread.id)
                        ans = messages.data[0].content[0].text.value
                        st.session_state["messages"].append({"role": "assistant", "content": ans})
                        st.rerun()
                except Exception as e:
                    st.error(f"Lỗi kết nối AI: {e}")
