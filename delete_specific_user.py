"""
Script to delete a specific user from the database.
"""
import os
import re
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get database connection parameters from environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:root@localhost:5432/campuscrush_db")

def delete_specific_user():
    """
    Delete the user with email B22F0108AI045@fecid.paf-iast.edu.pk
    """
    email = "b22f0108ai045@fecid.paf-iast.edu.pk"  # Using lowercase as shown in the database table
    print(f"Attempting to delete user with email: {email}")
    
    # Step 1: Find the user
    conn = None
    cursor = None
    user_id = None
    user = None
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True  # Use autocommit for this query
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Find the user
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if not user:
            print(f"No user found with email: {email}")
            
            # Try with a case-insensitive search
            print("Trying case-insensitive search...")
            cursor.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(%s)", (email,))
            user = cursor.fetchone()
            
            if not user:
                print("Still no user found. Exiting.")
                cursor.close()
                conn.close()
                return
        
        # Print user details before deletion
        print(f"\nFound user to delete:")
        print(f"User ID: {user['id']}")
        print(f"Email: {user['email']}")
        print(f"Username: {user['username']}")
        print(f"Full Name: {user['full_name']}")
        print(f"Profile Picture: {user.get('profile_picture', 'None')}")
        
        user_id = user['id']
        
        # Close this initial connection
        cursor.close()
        conn.close()
        
        # Step 2: Check if the friendship tables exist
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True  # Use autocommit for these queries
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check for friendship_requests table
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'friendship_requests'
            )
        """)
        friendship_requests_exists = cursor.fetchone()['exists']
        
        # Check for friendships table
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'friendships'
            )
        """)
        friendships_exists = cursor.fetchone()['exists']
        
        # Close after checking
        cursor.close()
        conn.close()
        
        # Step 3: Check if user has a profile picture and delete it
        if user.get('profile_picture'):
            try:
                # Extract filename from profile_picture URL
                filename_match = re.search(r'profile_pictures/([^?]+)', user['profile_picture'])
                if filename_match:
                    filename = filename_match.group(1)
                    file_path = Path("uploads/profile_pictures") / filename
                    if os.path.exists(file_path):
                        print(f"Deleting profile picture: {file_path}")
                        os.remove(file_path)
                        print("Profile picture deleted successfully.")
                    else:
                        print(f"Profile picture file not found: {file_path}")
            except Exception as e:
                print(f"Error deleting profile picture: {e}")
        
        # Step 4: Delete related records in separate transactions
        print("\nDeleting related records...")
        
        # Delete reactions
        try:
            conn = psycopg2.connect(DATABASE_URL)
            conn.autocommit = False
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("DELETE FROM reactions WHERE user_id = %s", (user_id,))
            print(f"Deleted {cursor.rowcount} reactions")
            
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error deleting reactions: {e}")
            if conn:
                conn.rollback()
                cursor.close()
                conn.close()
        
        # Delete comments
        try:
            conn = psycopg2.connect(DATABASE_URL)
            conn.autocommit = False
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("DELETE FROM comments WHERE author_id = %s", (user_id,))
            print(f"Deleted {cursor.rowcount} comments")
            
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error deleting comments: {e}")
            if conn:
                conn.rollback()
                cursor.close()
                conn.close()
        
        # Delete notifications
        try:
            conn = psycopg2.connect(DATABASE_URL)
            conn.autocommit = False
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("DELETE FROM notifications WHERE user_id = %s", (user_id,))
            print(f"Deleted {cursor.rowcount} notifications")
            
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error deleting notifications: {e}")
            if conn:
                conn.rollback()
                cursor.close()
                conn.close()
        
        # Delete friendship requests if table exists
        if friendship_requests_exists:
            try:
                conn = psycopg2.connect(DATABASE_URL)
                conn.autocommit = False
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                cursor.execute("DELETE FROM friendship_requests WHERE sender_id = %s OR receiver_id = %s", (user_id, user_id))
                print(f"Deleted {cursor.rowcount} friendship requests")
                
                conn.commit()
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"Error deleting friendship requests: {e}")
                if conn:
                    conn.rollback()
                    cursor.close()
                    conn.close()
        else:
            print("Skipping friendship_requests: Table does not exist")
        
        # Delete friendships if table exists
        if friendships_exists:
            try:
                conn = psycopg2.connect(DATABASE_URL)
                conn.autocommit = False
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                cursor.execute("DELETE FROM friendships WHERE user_id = %s OR friend_id = %s", (user_id, user_id))
                print(f"Deleted {cursor.rowcount} friendships")
                
                conn.commit()
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"Error deleting friendships: {e}")
                if conn:
                    conn.rollback()
                    cursor.close()
                    conn.close()
        else:
            print("Skipping friendships: Table does not exist")
        
        # Clean up any reactions/comments on user's posts
        try:
            conn = psycopg2.connect(DATABASE_URL)
            conn.autocommit = False
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get the user's post IDs
            cursor.execute("SELECT id FROM posts WHERE author_id = %s", (user_id,))
            post_ids = [row['id'] for row in cursor.fetchall()]
            
            # Delete reactions and comments for these posts
            for post_id in post_ids:
                cursor.execute("DELETE FROM reactions WHERE post_id = %s", (post_id,))
                cursor.execute("DELETE FROM comments WHERE post_id = %s", (post_id,))
            
            print(f"Cleaned up reactions and comments for {len(post_ids)} posts")
            
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error cleaning up post reactions/comments: {e}")
            if conn:
                conn.rollback()
                cursor.close()
                conn.close()
        
        # Delete posts
        try:
            conn = psycopg2.connect(DATABASE_URL)
            conn.autocommit = False
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("DELETE FROM posts WHERE author_id = %s", (user_id,))
            print(f"Deleted {cursor.rowcount} posts")
            
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error deleting posts: {e}")
            if conn:
                conn.rollback()
                cursor.close()
                conn.close()
        
        # Verify all posts are deleted before attempting to delete user
        try:
            conn = psycopg2.connect(DATABASE_URL)
            conn.autocommit = True
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("SELECT COUNT(*) FROM posts WHERE author_id = %s", (user_id,))
            remaining_posts = cursor.fetchone()['count']
            
            if remaining_posts > 0:
                print(f"WARNING: User still has {remaining_posts} posts in the database!")
                print("Cannot safely delete user without violating foreign key constraints.")
                cursor.close()
                conn.close()
                return
            
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error verifying posts deletion: {e}")
            if conn:
                cursor.close()
                conn.close()
            return
        
        # Finally delete the user
        try:
            conn = psycopg2.connect(DATABASE_URL)
            conn.autocommit = False
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            deleted_count = cursor.rowcount
            
            if deleted_count > 0:
                conn.commit()
                print(f"✅ Successfully deleted user with email {user['email']}")
            else:
                conn.rollback()
                print(f"❌ Failed to delete user - no rows affected")
            
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error deleting user: {e}")
            if conn:
                conn.rollback()
                cursor.close()
                conn.close()
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        if conn and not conn.closed:
            conn.rollback()
            if cursor and not cursor.closed:
                cursor.close()
            conn.close()

if __name__ == "__main__":
    delete_specific_user() 