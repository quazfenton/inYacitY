"""
User Account Models and Authentication

Supports:
- User registration and authentication (OAuth/password)
- User profiles
- User event creation and management
- User event tickets/registrations
- User preferences
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
import hashlib
import secrets


class AuthProvider(Enum):
    """Authentication provider type"""
    LOCAL = "local"  # Password-based
    GOOGLE = "google"
    GITHUB = "github"
    FACEBOOK = "facebook"


class UserRole(Enum):
    """User role/permission level"""
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


@dataclass
class UserEventRegistration:
    """
    User registration for an event (ticket tracking)
    
    Attributes:
        id: Registration ID
        event_id: Event being registered for
        registered_at: When user registered
        ticket_number: Ticket number if limited tickets
        status: Registration status (registered, cancelled, attended)
    """
    id: str
    event_id: str
    registered_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    ticket_number: Optional[int] = None
    status: str = "registered"  # registered, cancelled, attended

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'event_id': self.event_id,
            'registered_at': self.registered_at,
            'ticket_number': self.ticket_number,
            'status': self.status
        }


@dataclass
class UserProfile:
    """
    User profile information
    
    Attributes:
        id: User ID (UUID)
        username: Unique username
        email: Email address
        full_name: Display name
        bio: User bio/description
        avatar_url: Profile picture URL
        major_city: Preferred city code
        preferences: User preferences (filtering, etc.)
        created_at: Account creation time
        last_login: Last login timestamp
    """
    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    major_city: Optional[str] = None
    preferences: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_login: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'bio': self.bio,
            'avatar_url': self.avatar_url,
            'major_city': self.major_city,
            'preferences': self.preferences,
            'created_at': self.created_at,
            'last_login': self.last_login
        }

    @staticmethod
    def from_dict(data: dict) -> 'UserProfile':
        return UserProfile(
            id=data['id'],
            username=data['username'],
            email=data['email'],
            full_name=data.get('full_name'),
            bio=data.get('bio'),
            avatar_url=data.get('avatar_url'),
            major_city=data.get('major_city'),
            preferences=data.get('preferences', {}),
            created_at=data.get('created_at', datetime.utcnow().isoformat()),
            last_login=data.get('last_login')
        )


@dataclass
class UserAccount:
    """
    User account with authentication and event management
    
    Attributes:
        profile: User profile information
        auth_provider: Authentication provider
        password_hash: Hashed password (if local auth)
        role: User role/permissions
        event_registrations: Events user registered for
        created_events: Events created by user
        metadata: Additional user data
        last_updated: Account last modification
        verified: Is email verified?
        active: Is account active?
    """
    profile: UserProfile
    auth_provider: AuthProvider = AuthProvider.LOCAL
    password_hash: Optional[str] = None
    role: UserRole = UserRole.USER
    event_registrations: List[UserEventRegistration] = field(default_factory=list)
    created_events: List[str] = field(default_factory=list)  # Event IDs
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    verified: bool = False
    active: bool = True
    tokens: Dict[str, str] = field(default_factory=dict)  # OAuth tokens, refresh tokens, etc.

    def set_password(self, password: str) -> None:
        """Hash and set password"""
        salt = secrets.token_hex(16)
        hash_obj = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        self.password_hash = f"{salt}${hash_obj.hex()}"

    def verify_password(self, password: str) -> bool:
        """Verify password against hash"""
        if not self.password_hash:
            return False
        
        try:
            salt, hash_hex = self.password_hash.split('$')
            hash_obj = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                100000
            )
            return hash_obj.hex() == hash_hex
        except:
            return False

    def register_for_event(self, event_id: str, ticket_number: Optional[int] = None) -> UserEventRegistration:
        """Register user for an event"""
        registration = UserEventRegistration(
            id=f"{self.profile.id}_{event_id}_{secrets.token_hex(8)}",
            event_id=event_id,
            ticket_number=ticket_number
        )
        self.event_registrations.append(registration)
        return registration

    def unregister_from_event(self, event_id: str) -> bool:
        """Unregister user from event"""
        original_length = len(self.event_registrations)
        self.event_registrations = [
            r for r in self.event_registrations
            if r.event_id != event_id
        ]
        return len(self.event_registrations) < original_length

    def create_event(self, event_id: str) -> None:
        """Add created event to user's list"""
        if event_id not in self.created_events:
            self.created_events.append(event_id)

    def remove_created_event(self, event_id: str) -> bool:
        """Remove created event from user's list"""
        if event_id in self.created_events:
            self.created_events.remove(event_id)
            return True
        return False

    def get_registered_events(self) -> List[str]:
        """Get list of events user registered for"""
        return [r.event_id for r in self.event_registrations]

    def is_registered_for(self, event_id: str) -> bool:
        """Check if user registered for event"""
        return any(r.event_id == event_id for r in self.event_registrations)

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Serialize user account to dictionary"""
        data = {
            'profile': self.profile.to_dict(),
            'auth_provider': self.auth_provider.value,
            'role': self.role.value,
            'event_registrations': [r.to_dict() for r in self.event_registrations],
            'created_events': self.created_events,
            'metadata': self.metadata,
            'last_updated': self.last_updated,
            'verified': self.verified,
            'active': self.active
        }
        
        # Only include sensitive data if requested
        if include_sensitive:
            data['password_hash'] = self.password_hash
            data['tokens'] = self.tokens
        
        return data

    @staticmethod
    def from_dict(data: dict) -> 'UserAccount':
        """Deserialize user account from dictionary"""
        profile = UserProfile.from_dict(data['profile'])
        
        auth_provider = AuthProvider(data.get('auth_provider', 'local'))
        role = UserRole(data.get('role', 'user'))
        
        registrations = [
            UserEventRegistration(**r) for r in data.get('event_registrations', [])
        ]
        
        return UserAccount(
            profile=profile,
            auth_provider=auth_provider,
            password_hash=data.get('password_hash'),
            role=role,
            event_registrations=registrations,
            created_events=data.get('created_events', []),
            metadata=data.get('metadata', {}),
            last_updated=data.get('last_updated', datetime.utcnow().isoformat()),
            verified=data.get('verified', False),
            active=data.get('active', True),
            tokens=data.get('tokens', {})
        )


class UserStore:
    """
    In-memory user storage for development
    
    Production: Replace with database (MySQL/PostgreSQL)
    """
    
    def __init__(self):
        """Initialize user store"""
        self.users: Dict[str, UserAccount] = {}
        self.username_index: Dict[str, str] = {}  # username -> user_id
        self.email_index: Dict[str, str] = {}      # email -> user_id

    def create_user(
        self,
        user_id: str,
        username: str,
        email: str,
        full_name: Optional[str] = None
    ) -> UserAccount:
        """Create new user account"""
        # Check for duplicates
        if username in self.username_index or email in self.email_index:
            raise ValueError("Username or email already exists")
        
        profile = UserProfile(
            id=user_id,
            username=username,
            email=email,
            full_name=full_name
        )
        
        user = UserAccount(profile=profile)
        
        # Add to store and indexes
        self.users[user_id] = user
        self.username_index[username] = user_id
        self.email_index[email] = user_id
        
        return user

    def get_user(self, user_id: str) -> Optional[UserAccount]:
        """Get user by ID"""
        return self.users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[UserAccount]:
        """Get user by username"""
        user_id = self.username_index.get(username)
        return self.users.get(user_id) if user_id else None

    def get_user_by_email(self, email: str) -> Optional[UserAccount]:
        """Get user by email"""
        user_id = self.email_index.get(email)
        return self.users.get(user_id) if user_id else None

    def authenticate(self, username: str, password: str) -> Optional[UserAccount]:
        """Authenticate user with username and password"""
        user = self.get_user_by_username(username)
        if user and user.verify_password(password):
            user.profile.last_login = datetime.utcnow().isoformat()
            return user
        return None

    def update_user(self, user_id: str, updates: dict) -> Optional[UserAccount]:
        """Update user information"""
        user = self.get_user(user_id)
        if not user:
            return None
        
        # Update profile fields
        if 'full_name' in updates:
            user.profile.full_name = updates['full_name']
        if 'bio' in updates:
            user.profile.bio = updates['bio']
        if 'avatar_url' in updates:
            user.profile.avatar_url = updates['avatar_url']
        if 'major_city' in updates:
            user.profile.major_city = updates['major_city']
        if 'preferences' in updates:
            user.profile.preferences.update(updates['preferences'])
        
        user.last_updated = datetime.utcnow().isoformat()
        return user

    def get_stats(self) -> dict:
        """Get user store statistics"""
        return {
            'total_users': len(self.users),
            'verified_users': sum(1 for u in self.users.values() if u.verified),
            'active_users': sum(1 for u in self.users.values() if u.active),
            'by_role': {
                role.value: sum(1 for u in self.users.values() if u.role == role)
                for role in UserRole
            }
        }
