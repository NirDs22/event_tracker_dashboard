"""Sidebar components and functionality."""

import streamlit as st
import json
import pathlib
import threading
import traceback
from monitoring.database import SessionLocal, Topic, Post
from monitoring.collectors import collect_topic, collect_all_topics_efficiently
from monitoring.scheduler import send_test_digest
from monitoring.secrets import get_secret


def render_newsletter_frequency_settings():
    """Render newsletter frequency settings."""
    st.sidebar.markdown("### 📧 Newsletter Settings")
    
    FREQ_FILE = pathlib.Path(".newsletter_freq.json")
    FREQ_OPTIONS = [
        ("Daily", {"type": "cron", "minute": 0, "hour": 8}),
        ("Weekly", {"type": "cron", "minute": 0, "hour": 8, "day_of_week": "mon"}),
        ("Monthly", {"type": "cron", "minute": 0, "hour": 8, "day": 1}),
        ("Every 2 days", {"type": "interval", "days": 2}),
        ("Every 3 days", {"type": "interval", "days": 3}),
        ("Every 4 days", {"type": "interval", "days": 4}),
        ("Every 5 days", {"type": "interval", "days": 5}),
        ("Every 6 days", {"type": "interval", "days": 6}),
    ]
    
    default_freq = "Daily"
    saved_freq = default_freq
    if FREQ_FILE.exists():
        try:
            saved_freq = json.loads(FREQ_FILE.read_text()).get("freq", default_freq)
        except Exception:
            saved_freq = default_freq
    
    freq_labels = [x[0] for x in FREQ_OPTIONS]
    selected_freq = st.sidebar.selectbox(
        "How often to send the newsletter?",
        freq_labels,
        index=freq_labels.index(saved_freq) if saved_freq in freq_labels else 0,
        key="newsletter_freq_selectbox"
    )
    
    if selected_freq != saved_freq:
        FREQ_FILE.write_text(json.dumps({"freq": selected_freq}))
        st.sidebar.success(f"✅ Frequency set to: {selected_freq}. Please restart the app to apply.")


def render_digest_email_section():
    """Render the digest email section."""
    with st.sidebar.expander("📧 Send Digest Mail Now (All Topics)", expanded=False):
        digest_email = st.text_input("Target Email Address", key="digest_all_email")
        
        # Track email sending status in session state
        if "email_sending" not in st.session_state:
            st.session_state.email_sending = False
        if "email_status" not in st.session_state:
            st.session_state.email_status = None
        
        # Show status if email is currently being sent
        if st.session_state.email_sending:
            st.info("📤 Sending email in background... You can continue using the app.")
        
        # Show results of previous send operation
        if st.session_state.email_status == "success":
            st.success(f"✅ Full digest sent to {st.session_state.get('last_email', '')}!")
            st.session_state.email_status = None  # Reset after showing
        elif st.session_state.email_status == "failure":
            st.error(f"❌ Failed to send digest to {st.session_state.get('last_email', '')}.")
            st.session_state.email_status = None  # Reset after showing
            
        if st.button("Send Full Digest Now", key="digest_all_btn", disabled=st.session_state.email_sending):
            if not digest_email:
                st.warning("Please enter an email address.")
            else:
                send_digest_email_background(digest_email)


def render_add_topic_section():
    """Render the add new topic section."""
    with st.sidebar.expander("➕ **Add New Topic**", expanded=True):
        name = st.text_input("📝 Topic or Person", placeholder="e.g., AI Technology, Elon Musk")
        
        col1, col2 = st.columns(2)
        with col1:
            icon = st.text_input("🎭 Icon", value="📌", help="Choose an emoji to represent this topic")
        with col2:
            color = st.color_picker("🎨 Color", "#667eea", help="Pick a theme color for this topic")
        
        keywords = st.text_input("🔍 Keywords", placeholder="AI, machine learning, technology", help="Comma-separated keywords to filter content")
        profiles = st.text_input("👥 Social Profiles", placeholder="@username, facebook.com/page", help="Social media profiles to monitor")
        
        if st.button("✨ **Create Topic**", type="primary", use_container_width=True) and name:
            create_new_topic(name, icon, color, keywords, profiles)


def render_test_email_section():
    """Render the test email section."""
    if get_secret("SMTP_HOST") or get_secret("SMTP_SERVER") or get_secret("BREVO_API"):
        with st.sidebar.expander("📧 **Test Email Digest**"):
            # Track test email sending status in session state
            if "test_email_sending" not in st.session_state:
                st.session_state.test_email_sending = False
            if "test_email_status" not in st.session_state:
                st.session_state.test_email_status = None
                
            test_email = st.text_input("📧 Test Email", placeholder="your@email.com")
            
            # Show status if email is currently being sent
            if st.session_state.test_email_sending:
                st.info("📤 Sending test email in background... You can continue using the app.")
            
            # Show results of previous send operation
            if st.session_state.test_email_status == "success":
                st.success(f"✅ Test digest sent to {st.session_state.get('last_test_email', '')}!")
                st.session_state.test_email_status = None  # Reset after showing
            elif st.session_state.test_email_status == "failure":
                st.error(f"❌ Failed to send test digest to {st.session_state.get('last_test_email', '')}.")
                st.session_state.test_email_status = None  # Reset after showing
            
            session = SessionLocal()
            topic_names = [t.name for t in session.query(Topic).all()]
            session.close()
            
            if topic_names:
                test_topic = st.selectbox("Select Topic", topic_names)
                if st.button("📨 **Send Test Digest**", use_container_width=True, disabled=st.session_state.test_email_sending) and test_email and test_topic:
                    send_test_digest_background(test_email, test_topic)
            else:
                st.info("Create topics first to test email digests")


def render_manage_topics_section():
    """Render the manage topics section."""
    with st.sidebar.expander("🗑️ **Manage Topics**"):
        session = SessionLocal()
        topic_names = [t.name for t in session.query(Topic).all()]
        session.close()
        
        if topic_names:
            remove_choice = st.selectbox("Select topic to delete", ["None"] + topic_names, 
                                       help="⚠️ This will permanently delete all data for this topic")
            
            if remove_choice != "None":
                st.warning(f"⚠️ You are about to delete '{remove_choice}' and ALL its data!")
                st.error("⚠️ **This action cannot be undone!**")
                
                # Simple confirmation with immediate deletion
                confirm_key = f"confirm_delete_{remove_choice}_{hash(remove_choice)}"
                if st.checkbox("✅ I understand this will permanently delete all data", key=confirm_key):
                    if st.button("🗑️ **DELETE FOREVER**", type="primary", use_container_width=True, 
                               help="This will immediately delete the topic and all its posts"):
                        # Direct deletion without additional confirmation
                        session_del = SessionLocal()
                        try:
                            to_del = session_del.query(Topic).filter_by(name=remove_choice).first()
                            if to_del:
                                deleted_topic_id = to_del.id
                                
                                # Count and delete associated posts
                                posts_count = session_del.query(Post).filter_by(topic_id=to_del.id).count()
                                session_del.query(Post).filter_by(topic_id=to_del.id).delete()
                                
                                # Delete the topic
                                session_del.delete(to_del)
                                session_del.commit()
                                
                                # If the deleted topic was currently selected, reset to home screen
                                if (hasattr(st.session_state, 'selected_topic') and 
                                    st.session_state.selected_topic == deleted_topic_id):
                                    st.session_state.selected_topic = None
                                
                                # Clear any related session states
                                keys_to_delete = [key for key in list(st.session_state.keys()) 
                                                if remove_choice in key and 'confirm_delete' in key]
                                for key in keys_to_delete:
                                    del st.session_state[key]
                                
                                st.success(f"✅ Deleted '{remove_choice}' and {posts_count} posts!")
                                st.info("🏠 Returning to home screen...")
                                st.rerun()
                            else:
                                st.error("❌ Topic not found!")
                        except Exception as e:
                            st.error(f"❌ Error deleting topic: {str(e)}")
                            session_del.rollback()
                        finally:
                            session_del.close()
                else:
                    st.info("👆 Check the box above to enable deletion")
        else:
            st.info("No topics to manage yet")


def render_collect_all_section():
    """Render the collect all topics section."""
    if st.sidebar.button("🔄 **Collect All Topics Now**", type="primary", use_container_width=True):
        with st.sidebar.expander("📊 **Collection Progress**", expanded=True):
            collect_all_topics()


def send_digest_email_background(digest_email):
    """Send digest email in background thread."""
    st.session_state.last_email = digest_email
    st.session_state.email_sending = True
    
    def send_digest_worker():
        try:
            from monitoring.notifier import create_digest_html, send_email
            session = SessionLocal()
            
            topics = session.query(Topic).all()
            all_posts = []
            for topic in topics:
                posts = (
                    session.query(Post)
                    .filter_by(topic_id=topic.id)
                    .order_by(Post.posted_at.desc())
                    .limit(10)
                    .all()
                )
                for post in posts:
                    all_posts.append({
                        'content': post.content,
                        'url': post.url,
                        'source': post.source,
                        'posted_at': post.posted_at,
                        'likes': post.likes,
                        'comments': post.comments,
                        'topic': topic.name
                    })
            
            session.close()
            
            if not all_posts:
                print("[DEBUG] No posts found for any topic.")
                st.session_state.email_status = "failure"
            else:
                summary = f"Digest includes {len(all_posts)} posts from {len(topics)} topics."
                html_body = create_digest_html("All Topics", all_posts, summary)
                print(f"[DEBUG] Sending digest to {digest_email} with {len(all_posts)} posts.")
                success = send_email(digest_email, "📰 Full Digest: All Topics", html_body, 'html')
                
                if success:
                    print(f"[DEBUG] Digest sent to {digest_email} successfully.")
                    st.session_state.email_status = "success"
                else:
                    print(f"[DEBUG] Failed to send digest to {digest_email}.")
                    st.session_state.email_status = "failure"
        except Exception as e:
            print(f"[DEBUG] Exception: {e}\n{traceback.format_exc()}")
            st.session_state.email_status = "failure"
        finally:
            st.session_state.email_sending = False
    
    thread = threading.Thread(target=send_digest_worker)
    thread.daemon = True
    thread.start()
    st.info("📤 Sending email in background... You can continue using the app.")
    st.rerun()


def send_test_digest_background(test_email, test_topic):
    """Send test digest email in background thread."""
    st.session_state.last_test_email = test_email
    st.session_state.test_email_sending = True
    
    def send_test_worker():
        try:
            session = SessionLocal()
            topic_obj = session.query(Topic).filter_by(name=test_topic).first()
            session.close()
            
            if topic_obj:
                success = send_test_digest(topic_obj.id, test_email)
                if success:
                    st.session_state.test_email_status = "success"
                    print(f"[DEBUG] Test digest sent to {test_email} successfully.")
                else:
                    st.session_state.test_email_status = "failure"
                    print(f"[DEBUG] Failed to send test digest to {test_email}.")
        except Exception as e:
            print(f"[DEBUG] Exception sending test digest: {e}\n{traceback.format_exc()}")
            st.session_state.test_email_status = "failure"
        finally:
            st.session_state.test_email_sending = False
    
    thread = threading.Thread(target=send_test_worker)
    thread.daemon = True
    thread.start()
    st.info("📤 Sending test email in background... You can continue using the app.")
    st.rerun()


def create_new_topic(name, icon, color, keywords, profiles):
    """Create a new topic."""
    session = SessionLocal()
    topic_names = [t.name for t in session.query(Topic).all()]
    
    if name not in topic_names:
        with st.spinner(f"Creating topic '{name}'..."):
            topic = Topic(
                name=name,
                keywords=keywords,
                profiles=profiles,
                color=color,
                icon=icon,
            )
            session.add(topic)
            session.commit()
            session.refresh(topic)

            def progress(msg: str) -> None:
                st.sidebar.info(f"{icon} {msg}")

            collect_topic(topic, progress=progress, force=True)
            st.sidebar.success(f"✅ Topic '{name}' created successfully!")
    else:
        st.sidebar.error("⚠️ Topic already exists!")
    
    session.close()


def collect_all_topics():
    """Collect data for all topics."""
    session = SessionLocal()
    all_topics = session.query(Topic).all()
    session.close()
    
    # Show efficiency information
    if len(all_topics) > 1:
        st.info(f"⚡ Using efficient collection: Collecting by source first for {len(all_topics)} topics")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    errors: list[str] = []
    
    if len(all_topics) > 1:
        # Use efficient collection for multiple topics
        status_text.text("🚀 Using efficient collection method...")
        progress_bar.progress(0.1)
        
        def progress(msg: str):
            status_text.text(f"⚡ {msg}")
        
        errors.extend(collect_all_topics_efficiently(all_topics, progress=progress))
        progress_bar.progress(1.0)
        
    else:
        # Use traditional method for single topic
        for idx, t in enumerate(all_topics):
            status_text.text(f"Collecting {t.icon} {t.name}...")
            progress_bar.progress((idx + 1) / len(all_topics))
            
            def progress(msg: str, ic=t.icon):
                status_text.text(f"{ic} {msg}")
            
            errors.extend(collect_topic(t, progress=progress))
    
    if errors:
        st.sidebar.error("⚠️ Some collections failed:")
        for err in errors[:3]:  # Show only first 3 errors
            st.sidebar.error(f"• {err}")
        if len(errors) > 3:
            st.sidebar.error(f"... and {len(errors) - 3} more errors")
    else:
        st.sidebar.success("✅ All collections completed successfully!")
    
    progress_bar.progress(1.0)
    status_text.text("✅ Collection finished!")
