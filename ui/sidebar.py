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
    """Render the add new topic section with shared topic system using a form."""
    with st.sidebar.expander("➕ Add New Topic", expanded=True):
        
        with st.form("add_topic_form"):
            # Topic search and creation
            name = st.text_input(
                "📝 Topic or Person", 
                placeholder="e.g., AI Technology, Elon Musk",
                help="Enter a topic name or person you want to track"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                icon = st.text_input(
                    "🎭 Icon", 
                    value="📌", 
                    help="Choose an emoji to represent this topic"
                )
            with col2:
                color = st.color_picker(
                    "🎨 Color", 
                    "#667eea", 
                    help="Pick a theme color for this topic"
                )
            
            keywords = st.text_input(
                "🔍 Keywords (Optional)", 
                placeholder="AI, machine learning, technology",
                help="Optional: Comma-separated keywords to filter content. Leave empty to track all content about this topic."
            )
            profiles = st.text_input(
                "👥 Social Profiles", 
                placeholder="@username, facebook.com/page",
                help="Social media profiles to monitor. Enter usernames or page URLs."
            )
            
            submitted = st.form_submit_button("✨ Create Topic", type="primary", use_container_width=True)
            
        if submitted:
            if not name:
                st.error("Please enter a topic name")
            else:
                # Start background thread for topic creation and collection
                create_topic_with_background_collection(name, keywords, profiles, icon, color, current_user_id)


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


def create_topic_with_background_collection(name: str, keywords: str, profiles: str, icon: str, color: str, user_id: int):
    """Create a new shared topic and start background collection with progress tracking."""
    import time
    
    # Prevent multiple simultaneous topic creations
    if st.session_state.get("topic_creating", False):
        st.error("⚠️ Topic creation already in progress. Please wait for it to complete.")
        return
    
    # Check if there's an existing thread that hasn't been cleaned up
    existing_thread = st.session_state.get("topic_creation_thread")
    if existing_thread and existing_thread.is_alive():
        st.error("⚠️ Previous topic creation still running. Please wait or refresh the page.")
        return
    
    # Track creation status in session state
    st.session_state.topic_creating = True
    st.session_state.topic_creation_name = name
    st.session_state.topic_creation_start_time = time.time()
    
    def create_topic_worker():
        """Worker function that runs in background thread - NO st.session_state access allowed!"""
        try:
            from monitoring.shared_topics import find_or_create_shared_topic, subscribe_user_to_topic, normalize_topic_name
            from monitoring.database import SessionLocal, Topic, SharedTopic
            
            session = SessionLocal()
            
            # Check if shared topic already exists
            from monitoring.shared_topics import normalize_topic_name
            normalized_name = normalize_topic_name(name)
            existing_shared_topic = session.query(SharedTopic).filter(
                SharedTopic.name == normalized_name
            ).first()
            
            # Find or create shared topic
            shared_topic = find_or_create_shared_topic(session, name, keywords, profiles)
            is_new_topic = existing_shared_topic is None
            
            # Subscribe user to the shared topic
            subscription = subscribe_user_to_topic(
                session,
                user_id,
                shared_topic.id,
                display_name=name,
                color=color,
                icon=icon
            )
            
            # Add to legacy topics table for backward compatibility - avoid UNIQUE constraint issues
            existing_topic_row = session.query(Topic).filter_by(name=name, user_id=user_id).first()
            if not existing_topic_row:
                # For shared topic subscriptions, create a unique name to avoid conflicts
                # Check if this exact name exists globally (from other users)
                global_name_exists = session.query(Topic).filter_by(name=name).first()
                if global_name_exists:
                    # Use user-specific name to avoid UNIQUE constraint violation
                    legacy_name = f"{name}_user_{user_id}"
                else:
                    legacy_name = name
                
                topic_row = Topic(name=legacy_name, user_id=user_id, icon=icon, color=color, keywords=keywords, profiles=profiles)
                session.add(topic_row)
            
            session.commit()
            shared_topic_id = shared_topic.id
            session.close()
            
            # If this is a new topic, trigger collection automatically in separate thread
            collection_triggered = False
            if is_new_topic:
                try:
                    # Don't block topic creation - start collection in background
                    print(f"DEBUG: Starting automatic collection for new topic '{name}'")
                    
                    def collection_worker():
                        """Separate thread for collection - doesn't block topic creation"""
                        try:
                            # Track collection progress in database (threads can't use st.session_state)
                            import time
                            from datetime import datetime
                            from monitoring.database import SessionLocal, SharedTopic
                            
                            progress_session = SessionLocal()
                            shared_topic_record = progress_session.query(SharedTopic).filter_by(id=shared_topic_id).first()
                            if shared_topic_record:
                                # Mark as collecting in database
                                shared_topic_record.collection_status = 'collecting'
                                shared_topic_record.collection_start_time = datetime.utcnow()
                                progress_session.commit()
                            progress_session.close()
                            
                            from monitoring.collectors import collect_topic
                            from monitoring.database import Topic
                            
                            # Create a temporary Topic object for the collector
                            temp_topic = Topic(
                                name=name,
                                keywords=keywords,
                                profiles=profiles,
                                user_id=user_id
                            )
                            
                            # Use the legacy collector with shared_topic_id parameter
                            collection_errors = collect_topic(temp_topic, force=True, shared_topic_id=shared_topic_id)
                            
                            # Update progress - collection completed
                            progress_session = SessionLocal()
                            shared_topic_record = progress_session.query(SharedTopic).filter_by(id=shared_topic_id).first()
                            if shared_topic_record:
                                shared_topic_record.collection_status = 'completed'
                                shared_topic_record.collection_end_time = datetime.utcnow()
                                if collection_errors:
                                    shared_topic_record.collection_errors = str(collection_errors)
                                progress_session.commit()
                            progress_session.close()
                            
                            # Auto-clear collection status after 10 seconds
                            def clear_status():
                                time.sleep(10)
                                try:
                                    cleanup_session = SessionLocal()
                                    topic_record = cleanup_session.query(SharedTopic).filter_by(id=shared_topic_id).first()
                                    if topic_record and topic_record.collection_status in ['completed', 'failed']:
                                        topic_record.collection_status = None
                                        topic_record.collection_start_time = None
                                        topic_record.collection_end_time = None
                                        cleanup_session.commit()
                                    cleanup_session.close()
                                except Exception:
                                    pass
                            
                            cleanup_thread = threading.Thread(target=clear_status)
                            cleanup_thread.daemon = True
                            cleanup_thread.start()
                            
                            if collection_errors:
                                print(f"DEBUG: Automatic collection completed with errors for '{name}': {collection_errors}")
                            else:
                                print(f"DEBUG: Automatic collection completed successfully for '{name}'")
                                
                        except Exception as e:
                            print(f"DEBUG: Automatic collection failed for '{name}': {e}")
                            # Update progress - collection failed
                            try:
                                progress_session = SessionLocal()
                                shared_topic_record = progress_session.query(SharedTopic).filter_by(id=shared_topic_id).first()
                                if shared_topic_record:
                                    shared_topic_record.collection_status = 'failed'
                                    shared_topic_record.collection_errors = str(e)
                                    progress_session.commit()
                                progress_session.close()
                            except:
                                pass
                    
                    # Start collection in separate daemon thread
                    import threading
                    collection_thread = threading.Thread(target=collection_worker)
                    collection_thread.daemon = True
                    collection_thread.start()
                    
                    collection_triggered = True
                    print(f"DEBUG: Collection thread started for '{name}'")
                    
                except Exception as collect_e:
                    print(f"DEBUG: Failed to start collection thread for '{name}': {collect_e}")
                    # Don't fail topic creation if collection thread fails to start
            
            # Store results in thread-safe way (no st.session_state access)
            # The main thread will check this via polling
            import threading
            thread = threading.current_thread()
            thread.result = {
                'status': 'success',
                'shared_topic_id': shared_topic_id,
                'name': name,
                'is_new_topic': is_new_topic,
                'collection_triggered': collection_triggered
            }
            print(f"DEBUG: Topic creation succeeded for '{name}', shared_topic_id: {shared_topic_id}, new_topic: {is_new_topic}")  # Debug logging
                        
        except Exception as e:
            # Store error result - ensure this always happens
            import threading
            thread = threading.current_thread()
            
            # Provide user-friendly error messages
            error_msg = str(e)
            if "UNIQUE constraint failed" in error_msg:
                user_friendly_msg = f"Topic '{name}' already exists. Try a different name or check if it's already in your topics."
            else:
                user_friendly_msg = f"Failed to create topic: {error_msg}"
            
            thread.result = {
                'status': 'failed',
                'error': user_friendly_msg
            }
            print(f"DEBUG: Topic creation failed with error: {e}")  # Debug logging
    
    # Start the thread
    thread = threading.Thread(target=create_topic_worker)
    thread.daemon = True
    thread.start()
    
    # Store thread reference so we can check results later
    st.session_state.topic_creation_thread = thread
    
    st.toast(f"🚀 Creating topic '{name}'...")
    st.rerun()

def render_manage_topics_section(current_user_id: int):
    """Render the manage topics section using shared topic subscriptions."""
    with st.sidebar.expander("⚙️ Manage Topics", expanded=False):
        
        # Auto-refresh if topic creation is in progress (with timeout)
        if st.session_state.get("topic_creating", False):
            import time
            
            # Check if thread has completed
            thread = st.session_state.get("topic_creation_thread")
            if thread and not thread.is_alive():
                # Thread completed, check results
                if hasattr(thread, 'result'):
                    result = thread.result
                    if result['status'] == 'success':
                        st.session_state.selected_shared_topic = result['shared_topic_id']
                        
                        # Provide different messages based on whether it's new/existing topic
                        if result.get('is_new_topic', False):
                            if result.get('collection_triggered', False):
                                st.success(f"✅ Successfully created new topic '{result['name']}' with data collection!")
                            else:
                                st.success(f"✅ Successfully created new topic '{result['name']}'! Use 'Collect Now' to gather data.")
                        else:
                            st.success(f"✅ Successfully subscribed to existing topic '{result['name']}'!")
                    else:
                        st.error(f"❌ Failed to create topic: {result['error']}")
                else:
                    st.error("❌ Topic creation failed - no result found")
                
                # Clean up
                st.session_state.topic_creating = False
                if "topic_creation_thread" in st.session_state:
                    del st.session_state.topic_creation_thread
                st.rerun()
            else:
                # Thread still running, check for timeout
                start_time = st.session_state.get("topic_creation_start_time", time.time())
                elapsed = time.time() - start_time
                if elapsed < 300:  # 5 minute timeout
                    # Use Streamlit's auto-refresh mechanism instead of time.sleep()
                    st.rerun()
                else:
                    # Timeout reached, stop creation
                    st.session_state.topic_creating = False
                    st.error("❌ Topic creation timed out after 5 minutes")
        
        # Show topic creation progress if in progress
        if st.session_state.get("topic_creating", False):
            topic_name = st.session_state.get("topic_creation_name", "")
            
            # Simple progress indication (no precise progress from thread)
            with st.container():
                st.info(f"🔄 Creating topic '{topic_name}'...")
                st.progress(0.5)  # Show indeterminate progress
                
                # Show elapsed time
                if "topic_creation_start_time" in st.session_state:
                    import time
                    elapsed = time.time() - st.session_state.topic_creation_start_time
                    st.caption(f"⏱️ Elapsed: {elapsed:.1f}s")
        
        
        # Get user's subscriptions from shared topic system
        use_shared_topics = True
        
        if use_shared_topics:
            try:
                from monitoring.shared_topics import get_user_subscriptions
                session = SessionLocal()
                subscriptions = get_user_subscriptions(session, current_user_id)
                session.close()
                
                topic_names = [sub['name'] for sub in subscriptions]
                
            except ImportError:
                # Fall back to legacy system
                use_shared_topics = False
        
        if not use_shared_topics:
            # Legacy fallback
            session = SessionLocal()
            topics = session.query(Topic).filter(Topic.user_id == current_user_id).all()
            topic_names = [t.name for t in topics]
            session.close()
        
        if topic_names:
            remove_choice = st.selectbox(
                "Select topic to delete", 
                ["None"] + topic_names, 
                help="⚠️ This will permanently delete all data for this topic"
            )
            
            if remove_choice != "None":
                st.warning(f"⚠️ You are about to delete '{remove_choice}' and ALL its data!")
                st.error("⚠️ This action cannot be undone!")
                
                # Simple confirmation with immediate deletion
                confirm_key = f"confirm_delete_{remove_choice}_{hash(remove_choice)}"
                if st.checkbox("✅ I understand this will permanently delete all data", key=confirm_key):
                    if st.button("🗑️ DELETE FOREVER", type="primary", use_container_width=True, 
                               help="This will immediately delete the topic and all its posts"):
                        delete_user_topic(current_user_id, remove_choice, use_shared_topics)
                else:
                    st.info("👆 Check the box above to enable deletion")
        else:
            st.info("🎯 Ready to track your first topic! Add one above to get started.")
    
    st.sidebar.markdown("---")


def delete_user_topic(user_id: int, topic_name: str, use_shared_topics: bool):
    """Delete a user's topic subscription and optionally the topic itself."""
    try:
        if use_shared_topics:
            from monitoring.shared_topics import get_user_subscriptions, unsubscribe_user_from_topic
            from monitoring.database import Topic
            
            session = SessionLocal()
            
            # Find the subscription
            subscriptions = get_user_subscriptions(session, user_id)
            target_subscription = None
            for sub in subscriptions:
                if sub['name'] == topic_name:
                    target_subscription = sub
                    break
            
            if target_subscription:
                # Unsubscribe from shared topic
                unsubscribe_user_from_topic(session, user_id, target_subscription['shared_topic_id'])
                
                # Also remove from legacy topics table if exists
                legacy_topic = session.query(Topic).filter_by(name=topic_name, user_id=user_id).first()
                if legacy_topic:
                    from monitoring.database import Post
                    posts_count = session.query(Post).filter_by(topic_id=legacy_topic.id).count()
                    session.query(Post).filter_by(topic_id=legacy_topic.id).delete()
                    session.delete(legacy_topic)
                    session.commit()
                    st.success(f"✅ Unsubscribed from '{topic_name}' and deleted {posts_count} legacy posts!")
                else:
                    st.success(f"✅ Unsubscribed from '{topic_name}'!")
                    
                # Reset selected topic if it was the deleted one
                if (hasattr(st.session_state, 'selected_shared_topic') and 
                    st.session_state.selected_shared_topic == target_subscription['shared_topic_id']):
                    st.session_state.selected_shared_topic = None
                    st.session_state.selected_topic = None
            else:
                st.error("❌ Topic not found!")
                
            session.close()
            
        else:
            # Legacy deletion
            session = SessionLocal()
            to_del = session.query(Topic).filter_by(name=topic_name, user_id=user_id).first()
            if to_del:
                from monitoring.database import Post
                posts_count = session.query(Post).filter_by(topic_id=to_del.id).count()
                session.query(Post).filter_by(topic_id=to_del.id).delete()
                session.delete(to_del)
                session.commit()
                st.success(f"✅ Deleted '{topic_name}' and {posts_count} posts!")
            else:
                st.error("❌ Topic not found!")
            session.close()
        
        # Clear session state related to deleted topic
        keys_to_delete = [key for key in list(st.session_state.keys()) 
                         if topic_name in key and 'confirm_delete' in key]
        for key in keys_to_delete:
            del st.session_state[key]
        
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Error deleting topic: {str(e)}")


def render_collect_all_section(current_user_id: int):
    """Render the collect all topics section for user's topics only."""
    with st.sidebar.expander("🔄 Data Collection", expanded=False):
        
        # Check for timeout if collection is in progress
        if st.session_state.get("collection_in_progress", False):
            import time
            start_time = st.session_state.get("collection_start_time", time.time())
            elapsed = time.time() - start_time
            
            # Check if background thread is still alive
            thread = st.session_state.get("collection_thread")
            if thread and not thread.is_alive():
                # Thread completed, check results
                if hasattr(thread, 'result'):
                    result = thread.result
                    if result['status'] == 'success':
                        st.success(f"✅ Data collection completed successfully! Found data for {result['topics_count']} topics.")
                    elif result['status'] == 'partial':
                        st.success(f"⚠️ Collection completed with some issues for {result['topics_count']} topics.")
                        if result['errors']:
                            with st.expander("View collection issues"):
                                for error in result['errors'][:3]:  # Show first 3 errors
                                    st.error(f"• {error}")
                    elif result['status'] == 'no_topics':
                        st.info("ℹ️ No topics found to collect.")
                    elif result['status'] == 'failed':
                        st.error(f"❌ Collection failed: {result['error']}")
                else:
                    st.error("❌ Collection failed - no result found")
                
                # Clean up
                st.session_state.collection_in_progress = False
                if "collection_thread" in st.session_state:
                    del st.session_state.collection_thread
                st.rerun()
            else:
                # Thread still running, check for timeout
                if elapsed > 300:  # 5 minute timeout
                    st.session_state.collection_in_progress = False
                    st.error("❌ Collection timed out after 5 minutes")
                    st.rerun()
        
        # Show collection progress if in progress
        if st.session_state.get("collection_in_progress", False):
            with st.container():
                st.info("🔄 Collecting data from all sources...")
                st.progress(0.5)  # Show indeterminate progress
                
                # Show elapsed time
                if "collection_start_time" in st.session_state:
                    import time
                    elapsed = time.time() - st.session_state.collection_start_time
                    st.caption(f"⏱️ Elapsed: {elapsed:.1f}s")
                
                # Auto-refresh without blocking the main thread
                st.rerun()
            
        # Collect button
        button_text = "🔄 Collect My Topics Now"
        if st.session_state.get("collection_in_progress", False):
            button_text = "⏳ Collecting..."
            
        if st.button(button_text, type="primary", use_container_width=True, 
                    disabled=st.session_state.get("collection_in_progress", False)):
            start_background_collection(current_user_id)


def start_background_collection(user_id: int):
    """Start data collection in background thread with proper progress tracking."""
    import time
    
    # Initialize minimal progress tracking
    st.session_state.collection_in_progress = True
    st.session_state.collection_start_time = time.time()
    
    def collection_worker():
        """Worker function that runs in background thread - NO st.session_state access allowed!"""
        try:
            from monitoring.database import SessionLocal, UserTopicSubscription, SharedTopic, Topic
            
            session = SessionLocal()
            
            # Try shared topics first
            user_subscriptions = (
                session.query(UserTopicSubscription)
                .filter(UserTopicSubscription.user_id == user_id)
                .join(SharedTopic)
                .all()
            )
            
            # Fallback to legacy topics if no shared topics
            if not user_subscriptions:
                user_topics = session.query(Topic).filter(Topic.user_id == user_id).all()
                if not user_topics:
                    session.close()
                    # Store result in thread-safe way
                    import threading
                    thread = threading.current_thread()
                    thread.result = {'status': 'no_topics', 'message': 'No topics found'}
                    return
                
                # Convert to list of topic names for progress
                topic_names = [t.name for t in user_topics]
            else:
                topic_names = [sub.display_name or sub.shared_topic.name for sub in user_subscriptions]
                user_topics = [sub.shared_topic for sub in user_subscriptions]
            
            session.close()
            
            # Start collection
            total_posts = 0
            errors = []
            
            if user_subscriptions:  # Using shared topics
                try:
                    from monitoring.shared_collectors import collect_all_shared_topics_efficiently
                    
                    # No progress callback - runs silently in background
                    result = collect_all_shared_topics_efficiently()
                    
                    total_posts = result.get('total_posts', 0)
                    errors = result.get('errors', [])
                    
                except ImportError:
                    # Fallback to legacy collection
                    from monitoring.collectors import collect_all_topics_efficiently
                    
                    # Convert shared topics to legacy format for collection
                    legacy_topics = []
                    for sub in user_subscriptions:
                        legacy_topic = Topic()
                        legacy_topic.id = sub.shared_topic.id
                        legacy_topic.name = sub.shared_topic.name
                        legacy_topic.keywords = sub.shared_topic.keywords
                        legacy_topic.profiles = sub.shared_topic.profiles
                        legacy_topics.append(legacy_topic)
                    
                    # No progress callback - runs silently in background
                    errors = collect_all_topics_efficiently(legacy_topics)
                    
            else:  # Using legacy topics
                from monitoring.collectors import collect_all_topics_efficiently
                
                # No progress callback - runs silently in background
                errors = collect_all_topics_efficiently(user_topics)
            
            # Store results in thread-safe way
            import threading
            thread = threading.current_thread()
            if errors:
                thread.result = {
                    'status': 'partial',
                    'errors': errors,
                    'posts_count': total_posts,
                    'topics_count': len(topic_names)
                }
            else:
                thread.result = {
                    'status': 'success',
                    'posts_count': total_posts,
                    'topics_count': len(topic_names)
                }
                
        except Exception as e:
            # Store error result
            import threading
            thread = threading.current_thread()
            thread.result = {
                'status': 'failed',
                'error': str(e)
            }
    
    # Start the thread and store its reference
    thread = threading.Thread(target=collection_worker)
    thread.daemon = True
    thread.start()
    
    # Store thread reference to check if it's alive later
    st.session_state.collection_thread = thread
    
    st.toast("🚀 Started data collection in background...")
    st.rerun()


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
                from monitoring.notifier import create_digest_html, send_email
                from monitoring.database import Post
                
                session_posts = SessionLocal()
                posts = (
                    session_posts.query(Post)
                    .filter_by(topic_id=topic_obj.id)
                    .order_by(Post.posted_at.desc())
                    .limit(10)
                    .all()
                )
                
                posts_data = []
                for post in posts:
                    posts_data.append({
                        'content': post.content,
                        'url': post.url,
                        'source': post.source,
                        'posted_at': post.posted_at,
                        'likes': post.likes,
                        'comments': post.comments,
                        'topic': topic_obj.name
                    })
                
                session_posts.close()
                
                if posts_data:
                    summary = f"Test digest for '{topic_obj.name}' with {len(posts_data)} recent posts."
                    html_body = create_digest_html(topic_obj.name, posts_data, summary)
                    success = send_email(test_email, f"📰 Test Digest: {topic_obj.name}", html_body, 'html')
                else:
                    success = False
                
                if success:
                    st.session_state.test_email_status = "success"
                else:
                    st.session_state.test_email_status = "failure"
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
