import streamlit as st
import requests
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import time
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ============================
# MOCK FUNCTIONS FOR DATA
# ============================

def get_mock_mentions(topic):
    today = datetime.today()
    return pd.DataFrame({
        'date': pd.date_range(today.replace(day=1), periods=30),
        'mentions': [random.randint(0, 20) for _ in range(30)]
    })

def get_mock_news_summary(topic):
    return f"תקציר חדשות עבור '{topic}':\\nפוליטיקאי בשם {topic} העלה פוסט חדש בטוויטר. פורסמה כתבה בעיתון בנושא."

def get_mock_links(topic):
    return [
        f"https://news.example.com/{topic}/update1",
        f"https://reddit.com/r/news/comments/{random.randint(10000,99999)}"
    ]

def send_real_email(user_email, subject, summary):
    try:
        # Update with your actual email server settings
        sender_email = "youremail@example.com"
        sender_password = "yourpassword"
        smtp_server = "smtp.example.com"
        smtp_port = 587

        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = user_email
        msg["Subject"] = subject
        msg.attach(MIMEText(summary, "plain"))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)

        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

# ============================
# STREAMLIT UI
# ============================

st.set_page_config(page_title="מעקב חכם אחר חדשות", layout="wide")
st.title("📡 מערכת מעקב אחרי אנשי ציבור ונושאים חמים")

# Sidebar for user input
st.sidebar.header("⚙️ הגדרות משתמש")
topics = st.sidebar.text_area("הזן נושאים/שמות למעקב (שורה לכל נושא)", "ג'וני גוש\\nקולדפליי\\nחטיפה")
topics_list = [t.strip() for t in topics.split('\\n') if t.strip()]

user_email = st.sidebar.text_input("📧 כתובת מייל להתראות (אופציונלי)")
trigger_email = st.sidebar.button("שלח התראות חדשות במייל")

# Main dashboard
if topics_list:
    st.subheader("📊 דשבורד נושאים")
    for topic in topics_list:
        st.markdown(f"### 🔎 {topic}")

        col1, col2 = st.columns([3, 2])

        with col1:
            data = get_mock_mentions(topic)
            fig, ax = plt.subplots()
            ax.plot(data['date'], data['mentions'], marker='o')
            ax.set_title(f"כמות אזכורים עבור {topic} בחודש האחרון")
            ax.set_xlabel("תאריך")
            ax.set_ylabel("אזכורים")
            st.pyplot(fig)

        with col2:
            st.write("**סיכום AI:**")
            st.info(get_mock_news_summary(topic))

            st.write("**קישורים:**")
            for link in get_mock_links(topic):
                st.write(f"🔗 [{link}]({link})")

    if trigger_email and user_email:
        full_summary = "\\n\\n".join(get_mock_news_summary(topic) for topic in topics_list)
        if send_real_email(user_email, "התראות חדשות מהמעקב שלך", full_summary):
            st.success(f"התראה נשלחה ל-{user_email}")
        else:
            st.error("שליחת ההתראה נכשלה. ודא את פרטי הדוא\"ל שלך.")

else:
    st.warning("אנא הזן לפחות נושא אחד למעקב בעמוד הצדדי.")

