#!/usr/bin/env python3
"""
Automated digest email sender for GitHub Actions.
This script handles the automated sending of personalized digest emails to users
based on their preferences and frequency settings.
"""

import sys
import traceback
import argparse
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Any
from sqlalchemy import and_, func
from monitoring.database import SessionLocal, User
from ui.sidebar import generate_and_send_digest, calculate_next_digest_date


def get_eligible_users(session, specific_user_ids: str = None) -> List[User]:
    """Get users eligible for digest emails."""
    
    # Base query for eligible users
    base_query = session.query(User).filter(
        and_(
            User.digest_enabled == True,  # Only users with digest enabled
            User.email.isnot(None),       # Only users with email addresses
            User.is_guest == False        # Only registered users
        )
    )
    
    # Filter to specific user IDs if provided
    if specific_user_ids:
        try:
            user_ids = [int(x.strip()) for x in specific_user_ids.split(',') if x.strip().isdigit()]
            users = base_query.filter(User.id.in_(user_ids)).all()
            print(f'🎯 Filtering to specific users: {user_ids}')
        except ValueError:
            print('❌ Invalid user IDs provided')
            return []
    else:
        users = base_query.all()
    
    return users


def filter_users_by_frequency(users: List[User], force_send: bool = False) -> Tuple[List[User], List[Tuple[User, str]]]:
    """Filter users based on their digest frequency and last sent time."""
    
    users_to_send = []
    skipped_users = []
    
    for user in users:
        should_send = True
        skip_reason = ''
        
        if not force_send and user.last_digest_sent:
            # Check if enough time has passed based on user's frequency
            next_digest_date = calculate_next_digest_date(
                user.last_digest_sent, 
                user.digest_frequency or 'daily'
            )
            
            if next_digest_date and datetime.utcnow() < next_digest_date:
                should_send = False
                days_left = (next_digest_date - datetime.utcnow()).days
                skip_reason = f'next digest in {days_left} days ({user.digest_frequency})'
        
        if should_send:
            users_to_send.append(user)
        else:
            skipped_users.append((user, skip_reason))
    
    return users_to_send, skipped_users


def send_digest_to_user(user: User, test_mode: bool = False, test_email: str = None) -> Dict[str, Any]:
    """Send digest email to a single user."""
    
    email_address = user.email
    
    # In test mode, redirect to test email
    if test_mode and test_email:
        email_address = test_email
        print(f'🧪 TEST MODE: Redirecting {user.email} digest to {test_email}')
    
    print(f'📧 Sending digest to: {user.email} (User ID: {user.id})')
    
    # Generate and send personalized digest
    result = generate_and_send_digest(email_address, user.id)
    
    # Normalize result format
    if isinstance(result, dict):
        return result
    else:
        # Legacy boolean return
        return {
            'success': bool(result),
            'message': 'Digest sent successfully' if result else 'Failed to send digest',
            'status': 'success' if result else 'failed'
        }


def print_statistics(session) -> None:
    """Print database statistics after digest sending."""
    
    try:
        print('\n📈 Post-Digest Database Statistics:')
        
        # Total registered users
        total_users = session.query(func.count(User.id)).filter(User.is_guest == False).scalar()
        print(f'👥 Total registered users: {total_users}')
        
        # Users with digest enabled
        digest_enabled_users = session.query(func.count(User.id)).filter(
            and_(User.digest_enabled == True, User.is_guest == False)
        ).scalar()
        print(f'📧 Users with digest enabled: {digest_enabled_users}')
        
        # Users with email addresses
        users_with_email = session.query(func.count(User.id)).filter(
            and_(User.email.isnot(None), User.is_guest == False)
        ).scalar()
        print(f'✉️ Users with email addresses: {users_with_email}')
        
        # Recent digest sends (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(hours=24)
        recent_digests = session.query(func.count(User.id)).filter(
            User.last_digest_sent >= yesterday
        ).scalar()
        print(f'📨 Digests sent in last 24h: {recent_digests}')
        
        # Digest frequency distribution
        freq_dist = session.query(
            User.digest_frequency,
            func.count(User.id).label('count')
        ).filter(
            and_(User.digest_enabled == True, User.is_guest == False)
        ).group_by(User.digest_frequency).all()
        
        if freq_dist:
            print('📊 Digest frequency distribution:')
            for freq, count in freq_dist:
                print(f'   • {freq or "daily"}: {count} users')
    
    except Exception as e:
        print(f'❌ Error getting digest statistics: {e}')


def main():
    """Main digest sending function."""
    
    parser = argparse.ArgumentParser(description='Send automated digest emails')
    parser.add_argument('--test-mode', action='store_true', help='Run in test mode')
    parser.add_argument('--force-send', action='store_true', help='Force send even if already sent today')
    parser.add_argument('--specific-user-ids', type=str, help='Comma-separated user IDs to send to')
    parser.add_argument('--test-email', type=str, help='Test email address for test mode')
    
    args = parser.parse_args()
    
    print('📧 Starting automated digest email sending...')
    print(f'⏰ Digest sending started at: {datetime.utcnow()} UTC')
    
    if args.test_mode:
        print('🧪 Running in TEST MODE')
    
    session = SessionLocal()
    try:
        # Get eligible users
        users = get_eligible_users(session, args.specific_user_ids)
        
        if not users:
            print('ℹ️ No eligible users found for digest emails')
            return
        
        print(f'👥 Found {len(users)} eligible users for digest emails')
        
        # Filter users based on frequency and last sent time
        users_to_send, skipped_users = filter_users_by_frequency(users, args.force_send)
        
        print(f'📤 Will send digest to {len(users_to_send)} users')
        if skipped_users:
            print(f'⏭️ Skipping {len(skipped_users)} users:')
            for user, reason in skipped_users[:5]:  # Show first 5
                print(f'   • {user.email}: {reason}')
            if len(skipped_users) > 5:
                print(f'   ... and {len(skipped_users) - 5} more')
        
        if not users_to_send:
            print('ℹ️ No users need digest emails at this time')
            return
        
        # Send digest emails
        success_count = 0
        error_count = 0
        total_sent = 0
        
        for user in users_to_send:
            try:
                result = send_digest_to_user(user, args.test_mode, args.test_email)
                
                if result.get('success'):
                    success_count += 1
                    print(f'✅ Digest sent successfully to {user.email}')
                else:
                    error_count += 1
                    error_msg = result.get('message', 'Unknown error')
                    status = result.get('status', 'failed')
                    
                    if status == 'cooldown':
                        print(f'⏰ Skipped {user.email}: {error_msg}')
                    else:
                        print(f'❌ Failed to send to {user.email}: {error_msg}')
                
                total_sent += 1
                
                # Add delay between emails to avoid overwhelming SMTP
                if total_sent < len(users_to_send):
                    import time
                    time.sleep(2)  # 2 second delay between emails
                
            except Exception as e:
                error_count += 1
                print(f'❌ Exception sending to {user.email}: {e}')
                traceback.print_exc()
                continue
        
        # Print summary
        print(f'\n📊 Digest Email Summary:')
        print(f'✅ Successful sends: {success_count}')
        print(f'❌ Failed sends: {error_count}')
        print(f'📧 Total attempts: {success_count + error_count}')
        print(f'👥 Total eligible users: {len(users)}')
        print(f'⏭️ Skipped users: {len(skipped_users)}')
        print(f'⏰ Digest sending completed at: {datetime.utcnow()} UTC')
        
        # Print database statistics
        print_statistics(session)
        
        # Exit with error if more than 50% failed
        if error_count > success_count and (success_count + error_count) > 0:
            print('⚠️ More than 50% of digest sends failed - exiting with error')
            sys.exit(1)
        
    except Exception as e:
        print(f'❌ Fatal error in digest sending: {e}')
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == '__main__':
    main()
