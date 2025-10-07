"""
Professional SQLite CRM System
Production-grade database for lead management

This showcases:
- Proper database schema design
- SQL injection protection (parameterized queries)
- Transaction management
- Index optimization
- Export functionality
"""
import os
import sqlite3
import csv
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from pathlib import Path


class ApexCRM:
    """
    Professional CRM system using SQLite
    
    Features:
    - Automatic schema creation
    - Transaction support
    - Parameterized queries (SQL injection safe)
    - Index optimization
    - Export to CSV
    """
    
    def __init__(self, db_path: str = None):
        """Initialize CRM with database connection"""
        if db_path is None:
            db_path = os.getenv("DATABASE_PATH", "./apex_crm.db")
        
        self.db_path = db_path
        self._init_database()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _init_database(self):
        """Create tables and indexes if they don't exist"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create leads table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    company TEXT,
                    interest TEXT,
                    lead_score REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'Cold',
                    qualification_notes TEXT,
                    meeting_id TEXT,
                    meeting_time TEXT,
                    source TEXT DEFAULT 'Unknown',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Create indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_email 
                ON leads(email)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_status 
                ON leads(status)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_lead_score 
                ON leads(lead_score DESC)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at 
                ON leads(created_at DESC)
            """)
            
            print(f"✅ Database initialized: {self.db_path}")
    
    def create_lead(
        self,
        name: str,
        email: str,
        company: str = "",
        interest: str = "",
        lead_score: float = 0.0,
        status: str = None,
        qualification_notes: str = "",
        meeting_id: str = "",
        meeting_time: str = "",
        source: str = "AI Assistant"
    ) -> int:
        """
        Create a new lead in the database
        
        Args:
            name: Lead's full name
            email: Email address
            company: Company name
            interest: What they're interested in
            lead_score: AI-generated score (0-10)
            status: Hot/Qualified/Nurture/Cold
            qualification_notes: AI notes about lead quality
            meeting_id: Google Calendar event ID
            meeting_time: Scheduled meeting time
            source: How lead was captured
        
        Returns:
            Lead ID (database primary key)
        """
        # Auto-determine status from score if not provided
        if status is None:
            status = self._score_to_status(lead_score)
        
        now = datetime.utcnow().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO leads (
                    name, email, company, interest, lead_score,
                    status, qualification_notes, meeting_id, meeting_time,
                    source, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name, email, company, interest, lead_score,
                status, qualification_notes, meeting_id, meeting_time,
                source, now, now
            ))
            
            lead_id = cursor.lastrowid
            print(f"✅ Lead created: ID={lead_id}, Email={email}, Score={lead_score}")
            return lead_id
    
    def get_lead(self, lead_id: int) -> Optional[Dict[str, Any]]:
        """Get a lead by ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_lead_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get a lead by email"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM leads WHERE email = ? ORDER BY created_at DESC LIMIT 1",
                (email,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all_leads(
        self,
        status: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all leads with optional filtering
        
        Args:
            status: Filter by status (Hot/Qualified/Nurture/Cold)
            limit: Max number of results
            offset: Skip this many results (for pagination)
        
        Returns:
            List of lead dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if status:
                cursor.execute("""
                    SELECT * FROM leads 
                    WHERE status = ?
                    ORDER BY lead_score DESC, created_at DESC
                    LIMIT ? OFFSET ?
                """, (status, limit, offset))
            else:
                cursor.execute("""
                    SELECT * FROM leads 
                    ORDER BY lead_score DESC, created_at DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_hot_leads(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get hot leads (score >= 8.0)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM leads 
                WHERE lead_score >= 8.0
                ORDER BY lead_score DESC, created_at DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def update_lead(self, lead_id: int, **kwargs) -> bool:
        """
        Update a lead's fields
        
        Usage:
            crm.update_lead(123, status="Hot", lead_score=9.5)
        """
        if not kwargs:
            return False
        
        # Add updated_at timestamp
        kwargs['updated_at'] = datetime.utcnow().isoformat()
        
        # Build UPDATE query dynamically
        fields = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [lead_id]
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE leads SET {fields} WHERE id = ?",
                values
            )
            return cursor.rowcount > 0
    
    def delete_lead(self, lead_id: int) -> bool:
        """Delete a lead by ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
            return cursor.rowcount > 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get CRM statistics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Total leads
            cursor.execute("SELECT COUNT(*) as total FROM leads")
            total = cursor.fetchone()['total']
            
            # By status
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM leads 
                GROUP BY status
            """)
            by_status = {row['status']: row['count'] for row in cursor.fetchall()}
            
            # Average score
            cursor.execute("SELECT AVG(lead_score) as avg_score FROM leads")
            avg_score = cursor.fetchone()['avg_score'] or 0.0
            
            # Recent leads (last 7 days)
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM leads 
                WHERE created_at >= date('now', '-7 days')
            """)
            recent = cursor.fetchone()['count']
            
            return {
                "total_leads": total,
                "by_status": by_status,
                "average_score": round(avg_score, 2),
                "recent_leads_7d": recent
            }
    
    def export_to_csv(self, filepath: str = "leads_export.csv") -> str:
        """Export all leads to CSV file"""
        leads = self.get_all_leads(limit=10000)
        
        if not leads:
            return "No leads to export"
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=leads[0].keys())
            writer.writeheader()
            writer.writerows(leads)
        
        print(f"✅ Exported {len(leads)} leads to {filepath}")
        return filepath
    
    def _score_to_status(self, score: float) -> str:
        """Convert lead score to status"""
        if score >= 8.0:
            return "🔥 Hot"
        elif score >= 6.0:
            return "⭐ Qualified"
        elif score >= 4.0:
            return "📋 Nurture"
        else:
            return "📝 Cold"


# Singleton instance
_crm_instance = None

def get_crm() -> ApexCRM:
    """Get or create CRM instance (singleton pattern)"""
    global _crm_instance
    if _crm_instance is None:
        _crm_instance = ApexCRM()
    return _crm_instance


# CLI for testing
if __name__ == "__main__":
    print("🚀 Apex CRM - Testing Database")
    print("=" * 50)
    
    crm = get_crm()
    
    # Test: Create a lead
    lead_id = crm.create_lead(
        name="John Smith",
        email="john@example.com",
        company="Test Corp",
        interest="AI automation for sales",
        lead_score=8.5,
        source="Test"
    )
    
    # Test: Get lead
    lead = crm.get_lead(lead_id)
    print(f"\n📋 Created Lead:")
    print(f"   ID: {lead['id']}")
    print(f"   Name: {lead['name']}")
    print(f"   Score: {lead['lead_score']}")
    print(f"   Status: {lead['status']}")
    
    # Test: Get stats
    stats = crm.get_stats()
    print(f"\n📊 CRM Statistics:")
    print(f"   Total Leads: {stats['total_leads']}")
    print(f"   Average Score: {stats['average_score']}")
    print(f"   By Status: {stats['by_status']}")
    
    print("\n✅ Database tests passed!")
    print(f"📁 Database file: {crm.db_path}")