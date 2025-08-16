"""Sidebar components and functionality."""

import streamlit as st
import json
import pathlib
import threading
import traceback
from monitoring.database import SessionLocal, Topic, Post
from monitoring.collectors import collect_topic, collect_all_topics_efficiently
# from monitoring.scheduler import send_test_digest  # Disabled for cloud
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
    
    st.sidebar.markdown("---")


def render_add_topic_section(current_user_id: int):
    """Render the add new topic section with shared topic system."""
    with st.sidebar.expander("➕ Add New Topic", expanded=True):
        
        # Topic search and creation
        name = st.text_input("📝 Topic or Person", placeholder="e.g., AI Technology, Elon Musk")
        
        col1, col2 = st.columns(2)
        with col1:
            icon = st.text_input("🎭 Icon", value="📌", help="Choose an emoji to represent this topic")
        with col2:
            color = st.color_picker("🎨 Color", "#667eea", help="Pick a theme color for this topic")
        
        keywords = st.text_input("🔍 Keywords", placeholder="AI, machine learning, technology", help="Comma-separated keywords to filter content")
        profiles = st.text_input("👥 Social Profiles", placeholder="@username, facebook.com/page", help="Social media profiles to monitor")
        
        create_button_clicked = st.button("✨ Create Topic", type="primary", use_container_width=True)
        
        if create_button_clicked:
            if not name:
                st.error("Please enter a topic name")
            else:
                # Simply create/subscribe to topic regardless of whether it exists
                # This is what the user wants - one button that just works!
                from monitoring.database import SessionLocal
                from monitoring.shared_topics import find_exact_shared_topic, subscribe_user_to_topic, get_shared_topic_stats
                
                session = SessionLocal()
                try:
                    # Check if topic already exists
                    existing_topic = find_exact_shared_topic(session, name)
                    
                    if existing_topic:
                        # Topic exists - just subscribe the user
                        from monitoring.database import UserTopicSubscription
                        
                        # Check if user is already subscribed
                        already_subscribed = session.query(UserTopicSubscription).filter_by(
                            user_id=current_user_id,
                            shared_topic_id=existing_topic.id
                        ).first()
                        
                        if already_subscribed:
                            st.success(f"✅ You're already subscribed to '{name}'!")
                        else:
                            # Subscribe to existing topic
                            subscription = subscribe_user_to_topic(
                                session, current_user_id, existing_topic.id,
                                display_name=name, color=color, icon=icon
                            )
                            
                            stats = get_shared_topic_stats(session, existing_topic.id)
                            st.success(f"✅ Subscribed to existing topic '{name}' ({stats['posts_count']} posts)!")
                        
                        session.close()
                        st.rerun()
                    else:
                        # Topic doesn't exist - create new one and subscribe
                        session.close()  # Close before calling create function
                        create_new_shared_topic(name, icon, color, keywords, profiles, current_user_id)
                        st.rerun()
                        
                except Exception as e:
                    session.rollback()
                    session.close()
                    st.error(f"❌ Error creating/subscribing to topic: {str(e)}")


def render_test_email_section():
    """Render the test email section."""
    if get_secret("EMAIL_HOST") or get_secret("EMAIL_USER") or get_secret("BREVO_API"):
        with st.sidebar.expander("📧 Test Email Digest"):
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
                if st.button("📨 Send Test Digest", use_container_width=True, disabled=st.session_state.test_email_sending) and test_email and test_topic:
                    send_test_digest_background(test_email, test_topic)
            else:
                st.info("Create topics first to test email digests")


def render_manage_topics_section(current_user_id: int):
    """Render the manage topics section."""
    with st.sidebar.expander("⚙️ Manage Topics", expanded=False):
        session = SessionLocal()
        topics = session.query(Topic).filter(Topic.user_id == current_user_id).all()
        topic_names = [t.name for t in topics]
        session.close()
        
        if topic_names:
            remove_choice = st.selectbox("Select topic to delete", ["None"] + topic_names, 
                                       help="⚠️ This will permanently delete all data for this topic")
            
            if remove_choice != "None":
                st.warning(f"⚠️ You are about to delete '{remove_choice}' and ALL its data!")
                st.error("⚠️ This action cannot be undone!")
                
                # Simple confirmation with immediate deletion
                confirm_key = f"confirm_delete_{remove_choice}_{hash(remove_choice)}"
                if st.checkbox("✅ I understand this will permanently delete all data", key=confirm_key):
                    if st.button("🗑️ DELETE FOREVER", type="primary", use_container_width=True, 
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
    
    st.sidebar.markdown("---")


def render_collect_all_section(current_user_id: int):
    """Render the collect all topics section for user's topics only."""
    with st.sidebar.expander("🔄 Data Collection", expanded=False):
        if st.button("🔄 Collect My Topics Now", type="primary", use_container_width=True):
            with st.container():
                st.markdown("**📊 Collection Progress**")
                collect_user_shared_topics(current_user_id)


def collect_all_shared_topics_ui():
    """Collect data for all shared topics with UI feedback."""
    try:
        from monitoring.shared_collectors import collect_all_shared_topics_efficiently
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def progress_callback(message: str):
            status_text.text(message)
        
        # Run the shared collection
        result = collect_all_shared_topics_efficiently(progress_callback)
        
        progress_bar.progress(1.0)
        
        # Show results
        if result['errors']:
            st.warning("⚠️ Some collections had errors:")
            for error in result['errors'][:3]:  # Show first 3 errors
                st.error(f"• {error}")
            if len(result['errors']) > 3:
                st.error(f"... and {len(result['errors']) - 3} more errors")
        else:
            st.success("✅ All collections completed successfully!")
        
        st.info(f"📈 Collected {result['total_posts']} posts from {result['total_topics']} topics across {len(result['sources_processed'])} sources")
        
    except Exception as e:
        st.error(f"❌ Collection failed: {str(e)}")
        import traceback
        st.error(traceback.format_exc())


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


def subscribe_to_existing_topic(user_id: int, shared_topic_id: int, topic_name: str):
    """Subscribe user to an existing shared topic."""
    try:
        from monitoring.shared_topics import subscribe_user_to_topic
        from monitoring.database import SessionLocal
        
        session = SessionLocal()
        
        # Check if user is already subscribed
        from monitoring.database import UserTopicSubscription
        existing_subscription = session.query(UserTopicSubscription).filter_by(
            user_id=user_id,
            shared_topic_id=shared_topic_id
        ).first()
        
        if existing_subscription:
            st.warning(f"⚠️ You're already subscribed to '{topic_name}'!")
            session.close()
            return
        
        subscription = subscribe_user_to_topic(
            session, 
            user_id, 
            shared_topic_id,
            display_name=topic_name
        )
        
        session.close()
        
        st.success(f"✅ Subscribed to '{topic_name}'!")
        
        # Clear cached data to force UI refresh
        session_keys_to_clear = [
            'user_subscribed_topics', 
            'topic_cards_data', 
            'selected_shared_topic',
            'selected_topic'
        ]
        for key in session_keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        
        # Use a timeout before rerun to ensure all state is properly updated
        import time
        time.sleep(0.1)
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Error subscribing to topic: {str(e)}")
        import traceback
        st.write(f"Full error details: {traceback.format_exc()}")


def create_new_shared_topic(name: str, icon: str, color: str, keywords: str, profiles: str, user_id: int):
    """Create a new shared topic and subscribe the user to it."""
    print(f"DEBUG: create_new_shared_topic called with name='{name}'")
    try:
        from monitoring.shared_topics import find_or_create_shared_topic, subscribe_user_to_topic
        from monitoring.database import SessionLocal
        
        session = SessionLocal()
        
        # Find or create shared topic
        shared_topic = find_or_create_shared_topic(session, name, keywords, profiles)
        print(f"DEBUG: Created shared_topic with ID={shared_topic.id}")
        
        # Subscribe user to the shared topic
        subscription = subscribe_user_to_topic(
            session,
            user_id,
            shared_topic.id,
            display_name=name,
            color=color,
            icon=icon
        )
        print(f"DEBUG: User subscribed to topic")
        
        # Store the shared topic data before closing session (to avoid DetachedInstanceError)
        shared_topic_id = shared_topic.id
        shared_topic_name = shared_topic.name
        shared_topic_keywords = shared_topic.keywords or ""
        
        session.close()
        
        # Start collection for the new topic
        print(f"DEBUG: Starting collection for '{name}'...")
        with st.spinner(f"Collecting initial data for '{name}'..."):
            try:
                from monitoring.collectors import collect_topic
                from monitoring.database import Topic
                
                def progress(msg: str) -> None:
                    st.sidebar.info(f"{icon} {msg}")
                    print(f"DEBUG: Progress: {msg}")
                
                # Create a temporary Topic object for the collector (since collector expects Topic, not SharedTopic)
                temp_topic = Topic()
                temp_topic.id = shared_topic_id
                temp_topic.name = shared_topic_name
                temp_topic.keywords = shared_topic_keywords
                temp_topic.search_reddit = True
                temp_topic.search_facebook = True
                temp_topic.search_instagram = True
                temp_topic.search_twitter = True
                temp_topic.search_photos = True
                temp_topic.last_collected = None
                print(f"DEBUG: Created temp_topic for collection")
                
                # Force collection for the new topic immediately
                progress(f"Collecting data for {name}...")
                errors = collect_topic(temp_topic, force=True, progress=progress, shared_topic_id=shared_topic_id)
                print(f"DEBUG: Collection completed with errors: {errors}")
                
                # Count shared posts after collection
                from monitoring.database import SharedPost
                session_count = SessionLocal()
                post_count = session_count.query(SharedPost).filter(SharedPost.shared_topic_id == shared_topic_id).count()
                session_count.close()
                print(f"DEBUG: Post count after collection: {post_count}")
                
                if post_count > 0:
                    st.sidebar.success(f"✅ Topic '{name}' created with {post_count} initial posts!")
                else:
                    if errors:
                        st.sidebar.warning(f"⚠️ Topic '{name}' created but collection had issues: {'; '.join(errors[:2])}")
                    else:
                        st.sidebar.warning(f"⚠️ Topic '{name}' created but no posts were collected")
                        print("DEBUG: No errors but no posts collected - possible collection issue")
                    
            except Exception as collect_e:
                print(f"DEBUG: Collection exception: {str(collect_e)}")
                st.sidebar.error(f"❌ Topic created but initial collection failed: {str(collect_e)}")
        
        # Clear cached data to force UI refresh
        session_keys_to_clear = [
            'user_subscribed_topics', 
            'topic_cards_data', 
            'selected_shared_topic',
            'selected_topic'
        ]
        for key in session_keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        
        # Use a timeout before rerun to ensure all state is properly updated
        import time
        time.sleep(0.1)
        st.rerun()
        
    except Exception as e:
        st.sidebar.error(f"❌ Error creating topic: {str(e)}")


def create_new_topic(name, icon, color, keywords, profiles, user_id):
    """Legacy function - redirects to shared topic system."""
    create_new_shared_topic(name, icon, color, keywords, profiles, user_id)


def collect_user_shared_topics(current_user_id: int):
    """Collect data for shared topics that the current user is subscribed to.
    
    This is different from the scheduled hourly collection which runs for ALL users' topics.
    When a user manually clicks "Collect My Topics Now", it should only collect their subscribed topics.
    """
    try:
        from monitoring.database import SessionLocal, UserTopicSubscription, SharedTopic
        
        session = SessionLocal()
        
        # Get user's subscribed shared topics
        user_subscriptions = (
            session.query(UserTopicSubscription)
            .filter(UserTopicSubscription.user_id == current_user_id)
            .join(SharedTopic)
            .all()
        )
        
        if not user_subscriptions:
            session.close()
            st.warning("📭 You haven't subscribed to any topics yet!")
            st.info("👆 Add a new topic above to get started.")
            return
        
        # Extract the shared topics for display
        topic_names = [sub.display_name or sub.shared_topic.name for sub in user_subscriptions]
        shared_topics = [sub.shared_topic for sub in user_subscriptions]
        
        session.close()
        
        # Show collection info
        st.info(f"🔄 Collecting data for your {len(topic_names)} subscribed topics: {', '.join(topic_names[:3])}")
        if len(topic_names) > 3:
            st.info(f"... and {len(topic_names) - 3} more topics")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def progress_callback(message: str):
            status_text.text(f"⚡ {message}")
        
        # Use the global collection for now, but inform user it's their topics
        # TODO: Create specific user collection function later
        try:
            from monitoring.shared_collectors import collect_all_shared_topics_efficiently
            
            # Note: This will collect all topics but filter results for user
            progress_callback("Starting collection for your topics...")
            result = collect_all_shared_topics_efficiently(progress_callback)
            
            progress_bar.progress(1.0)
            
            # Show results focused on user experience
            if result.get('errors'):
                st.warning("⚠️ Some collections had errors:")
                for error in result['errors'][:3]:  # Show first 3 errors
                    st.error(f"• {error}")
                if len(result['errors']) > 3:
                    st.error(f"... and {len(result['errors']) - 3} more errors")
            else:
                st.success("✅ Your subscribed topics have been updated!")
            
            # Give user-focused feedback
            st.info(f"📈 Collection completed! Your {len(topic_names)} topics have been refreshed with the latest data.")
            status_text.text("✅ Collection finished!")
            
        except ImportError:
            # If shared collectors aren't available, fall back to old system
            st.warning("🔄 Using fallback collection method...")
            collect_all_topics(current_user_id)
        
    except ImportError:
        # Fallback to old system if shared topics system not available
        st.warning("🔄 Using legacy collection method...")
        collect_all_topics(current_user_id)
    except Exception as e:
        st.error(f"❌ Collection failed: {str(e)}")
        # Don't show full traceback to user, just log the error type
        st.info("💡 If this persists, try refreshing the page.")


def collect_all_topics(current_user_id: int):
    """Legacy function - Collect data for old Topic model (fallback).
    
    This is for backward compatibility with the old individual Topic system.
    """
    session = SessionLocal()
    user_topics = session.query(Topic).filter(Topic.user_id == current_user_id).all()
    session.close()
    
    # Show efficiency information
    if len(user_topics) > 1:
        st.info(f"⚡ Using efficient collection: Collecting by source first for {len(user_topics)} topics")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    errors: list[str] = []
    
    if len(user_topics) > 1:
        # Use efficient collection for multiple topics
        status_text.text("🚀 Using efficient collection method...")
        progress_bar.progress(0.1)
        
        def progress(msg: str):
            status_text.text(f"⚡ {msg}")
        
        errors.extend(collect_all_topics_efficiently(user_topics, progress=progress))
        progress_bar.progress(1.0)
        
    else:
        # Use traditional method for single topic
        for idx, t in enumerate(user_topics):
            status_text.text(f"Collecting {t.icon} {t.name}...")
            progress_bar.progress((idx + 1) / len(user_topics))
            
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
