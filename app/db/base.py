# Import all models here so Alembic can detect them
from app.db.session import Base

# Import all models below
from app.modules.user_management.models.user import User
from app.modules.posts.models.post import Post
from app.modules.posts.comments.models.comment import Comment
from app.modules.posts.reactions.models.reaction import Reaction
from app.modules.friendships.models.friendship import Friendship, FriendshipRequest
from app.modules.notifications.models.notification import Notification

# Add any other models that need to be included in migrations 