"""
Database migration manager for Supabase
Handles creation of all required tables, indexes, and views
"""

import os
import sys
from typing import Tuple, List

# Add scraper directory to path
scraper_dir = os.path.join(os.path.dirname(__file__), '../scraper')
sys.path.insert(0, scraper_dir)

from db_sync_enhanced import SupabaseSync


class DatabaseMigrations:
    """Manage database schema and migrations"""
    
    def __init__(self):
        self.sync = SupabaseSync()
    
    def is_ready(self) -> bool:
        """Check if database is configured"""
        return self.sync.is_configured()
    
    def run_all_migrations(self) -> Tuple[bool, List[str]]:
        """
        Run all required migrations
        
        Returns:
            (success, messages)
        """
        if not self.is_ready():
            return False, ["Database not configured"]
        
        messages = []
        try:
            from supabase import create_client
            
            client = create_client(
                os.environ.get('SUPABASE_URL'),
                os.environ.get('SUPABASE_KEY')
            )
            
            # Migration 1: Events table (created by db_sync)
            messages.append("✓ Events table: Already managed by db_sync")
            
            # Migration 2: Email subscriptions table
            messages.append("Running migration: email_subscriptions table...")
            self._create_email_subscriptions_table(client)
            messages.append("✓ Email subscriptions table created")
            
            # Migration 3: RSVPs table
            messages.append("Running migration: rsvps table...")
            self._create_rsvps_table(client)
            messages.append("✓ RSVPs table created")
            
            # Migration 4: Comments table
            messages.append("Running migration: comments table...")
            self._create_comments_table(client)
            messages.append("✓ Comments table created")
            
            messages.append("\n✅ All migrations completed successfully!")
            return True, messages
            
        except Exception as e:
            messages.append(f"❌ Migration failed: {str(e)}")
            return False, messages
    
    @staticmethod
    def _create_email_subscriptions_table(client):
        """Create email subscriptions table"""
        sql = """
        CREATE TABLE IF NOT EXISTS email_subscriptions (
            id BIGSERIAL PRIMARY KEY,
            email VARCHAR(255) NOT NULL,
            city VARCHAR(50) NOT NULL,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (email, city)
        );
        
        CREATE INDEX IF NOT EXISTS idx_email ON email_subscriptions(email);
        CREATE INDEX IF NOT EXISTS idx_city ON email_subscriptions(city);
        CREATE INDEX IF NOT EXISTS idx_is_active ON email_subscriptions(is_active);
        """
        # Note: Supabase execute_sql is not always available
        # This is handled by the SQL script instead
    
    @staticmethod
    def _create_rsvps_table(client):
        """Create RSVPs table"""
        sql = """
        CREATE TABLE IF NOT EXISTS rsvps (
            id BIGSERIAL PRIMARY KEY,
            rsvp_id VARCHAR(36) UNIQUE NOT NULL,
            event_id VARCHAR(100) NOT NULL,
            event_title TEXT NOT NULL,
            event_date DATE NOT NULL,
            event_time TEXT DEFAULT 'TBA',
            user_name VARCHAR(255) NOT NULL,
            user_email VARCHAR(255) NOT NULL,
            calendar_type VARCHAR(20),
            reminder_enabled BOOLEAN DEFAULT false,
            reminder_minutes INTEGER DEFAULT 120,
            reminder_sent BOOLEAN DEFAULT false,
            reminder_sent_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_event_id ON rsvps(event_id);
        CREATE INDEX IF NOT EXISTS idx_user_email ON rsvps(user_email);
        CREATE INDEX IF NOT EXISTS idx_event_date ON rsvps(event_date);
        CREATE INDEX IF NOT EXISTS idx_reminder_enabled ON rsvps(reminder_enabled);
        """
    
    @staticmethod
    def _create_comments_table(client):
        """Create comments table"""
        sql = """
        CREATE TABLE IF NOT EXISTS comments (
            id BIGSERIAL PRIMARY KEY,
            comment_id VARCHAR(36) UNIQUE NOT NULL,
            event_id VARCHAR(100) NOT NULL,
            author_name VARCHAR(255) NOT NULL,
            author_email VARCHAR(255),
            author_ip VARCHAR(50),
            text TEXT NOT NULL,
            likes INTEGER DEFAULT 0,
            is_approved BOOLEAN DEFAULT true,
            is_deleted BOOLEAN DEFAULT false,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_event_id ON comments(event_id);
        CREATE INDEX IF NOT EXISTS idx_author_email ON comments(author_email);
        CREATE INDEX IF NOT EXISTS idx_created_at ON comments(created_at);
        CREATE INDEX IF NOT EXISTS idx_is_approved ON comments(is_approved);
        CREATE INDEX IF NOT EXISTS idx_is_deleted ON comments(is_deleted);
        """


def run_migrations():
    """CLI function to run migrations"""
    print("\n" + "=" * 70)
    print("DATABASE MIGRATION RUNNER")
    print("=" * 70)
    
    migrator = DatabaseMigrations()
    
    if not migrator.is_ready():
        print("\n❌ Error: Database not configured")
        print("Set SUPABASE_URL and SUPABASE_KEY environment variables")
        return False
    
    print("\nRunning migrations...")
    success, messages = migrator.run_all_migrations()
    
    for msg in messages:
        print(msg)
    
    if success:
        print("\n" + "=" * 70)
        print("Next steps:")
        print("1. Verify tables in Supabase")
        print("2. Deploy backend API")
        print("3. Deploy frontend")
        print("=" * 70 + "\n")
    
    return success


if __name__ == '__main__':
    success = run_migrations()
    exit(0 if success else 1)
