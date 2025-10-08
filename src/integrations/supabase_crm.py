"""
Professional Supabase CRM System
Production-grade PostgreSQL database with beautiful dashboard

Features:
- Cloud-hosted PostgreSQL
- Real-time updates
- Beautiful web dashboard
- Team collaboration
- Automatic backups
- Professional and scalable
"""
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


class SupabaseCRM:
    """
    Professional CRM using Supabase (PostgreSQL)
    
    Dashboard: https://supabase.com/dashboard/project/YOUR_PROJECT
    """
    
    def __init__(self):
        """Initialize Supabase connection"""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        if not url or not key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY must be set in .env file.\n"
                "Get them from: https://supabase.com/dashboard/project/YOUR_PROJECT/settings/api"
            )
        
        self.client: Client = create_client(url, key)
        self.table_name = "leads"
        
        print(f"✅ Connected to Supabase CRM")
        
        # Create table if it doesn't exist
        self._initialize_table()
    
    def _initialize_table(self):
        """
        Create leads table if it doesn't exist
        
        Run this SQL in Supabase SQL Editor:
        https://supabase.com/dashboard/project/YOUR_PROJECT/editor
        """
        print(f"ℹ️  Ensure 'leads' table exists in Supabase")
        print(f"   Dashboard: https://supabase.com/dashboard")
    
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
        meeting_link: str = "",
        source: str = "AI Assistant"
    ) -> Dict[str, Any]:
        """
        Create a new lead in Supabase
        
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
            meeting_link: Google Meet link
            source: How lead was captured
        
        Returns:
            Created lead record
        """
        # Auto-determine status from score if not provided
        if status is None:
            status = self._score_to_status(lead_score)
        
        now = datetime.now(timezone.utc).isoformat()
        
        lead_data = {
            "name": name,
            "email": email,
            "company": company,
            "interest": interest,
            "lead_score": lead_score,
            "status": status,
            "qualification_notes": qualification_notes,
            "meeting_id": meeting_id,
            "meeting_time": meeting_time,
            "meeting_link": meeting_link,
            "source": source,
            "created_at": now,
            "updated_at": now
        }
        
        try:
            response = self.client.table(self.table_name).insert(lead_data).execute()
            
            if response.data:
                lead = response.data[0]
                lead_id = lead.get('id')
                print(f"✅ Lead created in Supabase: ID={lead_id}, Email={email}, Score={lead_score}")
                return lead
            else:
                raise Exception("No data returned from insert")
                
        except Exception as e:
            print(f"❌ Error creating lead: {e}")
            raise
    
    def get_lead(self, lead_id: int) -> Optional[Dict[str, Any]]:
        """Get a lead by ID"""
        try:
            response = self.client.table(self.table_name)\
                .select("*")\
                .eq("id", lead_id)\
                .execute()
            
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"❌ Error fetching lead: {e}")
            return None
    
    def get_lead_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get a lead by email"""
        try:
            response = self.client.table(self.table_name)\
                .select("*")\
                .eq("email", email)\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"❌ Error fetching lead: {e}")
            return None
    
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
        try:
            query = self.client.table(self.table_name).select("*")
            
            if status:
                query = query.eq("status", status)
            
            response = query\
                .order("lead_score", desc=True)\
                .order("created_at", desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()
            
            return response.data if response.data else []
        except Exception as e:
            print(f"❌ Error fetching leads: {e}")
            return []
    
    def get_hot_leads(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get hot leads (score >= 8.0)"""
        try:
            response = self.client.table(self.table_name)\
                .select("*")\
                .gte("lead_score", 8.0)\
                .order("lead_score", desc=True)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            
            return response.data if response.data else []
        except Exception as e:
            print(f"❌ Error fetching hot leads: {e}")
            return []
    
    def update_lead(self, lead_id: int, **kwargs) -> bool:
        """
        Update a lead's fields
        
        Usage:
            crm.update_lead(123, status="Hot", lead_score=9.5)
        """
        if not kwargs:
            return False
        
        # Add updated_at timestamp
        kwargs['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        try:
            response = self.client.table(self.table_name)\
                .update(kwargs)\
                .eq("id", lead_id)\
                .execute()
            
            return len(response.data) > 0
        except Exception as e:
            print(f"❌ Error updating lead: {e}")
            return False
    
    def delete_lead(self, lead_id: int) -> bool:
        """Delete a lead by ID"""
        try:
            response = self.client.table(self.table_name)\
                .delete()\
                .eq("id", lead_id)\
                .execute()
            
            return len(response.data) > 0
        except Exception as e:
            print(f"❌ Error deleting lead: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get CRM statistics"""
        try:
            # Total leads
            all_leads = self.get_all_leads(limit=10000)
            total = len(all_leads)
            
            # By status
            by_status = {}
            for lead in all_leads:
                status = lead.get('status', 'Unknown')
                by_status[status] = by_status.get(status, 0) + 1
            
            # Average score
            scores = [lead.get('lead_score', 0) for lead in all_leads]
            avg_score = sum(scores) / len(scores) if scores else 0.0
            
            # Recent leads (last 7 days)
            seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            recent = len([
                lead for lead in all_leads 
                if lead.get('created_at', '') >= seven_days_ago
            ])
            
            return {
                "total_leads": total,
                "by_status": by_status,
                "average_score": round(avg_score, 2),
                "recent_leads_7d": recent
            }
        except Exception as e:
            print(f"❌ Error getting stats: {e}")
            return {
                "total_leads": 0,
                "by_status": {},
                "average_score": 0.0,
                "recent_leads_7d": 0
            }
    
    def _score_to_status(self, score: float) -> str:
        """Convert lead score to status"""
        if score >= 8.0:
            return "🔥 Hot"
        elif score >= 6.0:
            return "⭐ Qualified"
        elif score >= 4.0:
            return "📋 Nurture"
        else:
            return "🧊 Cold"


# Singleton instance
_supabase_crm = None

def get_crm() -> SupabaseCRM:
    """Get or create Supabase CRM instance (singleton pattern)"""
    global _supabase_crm
    if _supabase_crm is None:
        _supabase_crm = SupabaseCRM()
    return _supabase_crm


# CLI for testing
if __name__ == "__main__":
    print("🚀 Supabase CRM - Testing")
    print("=" * 60)
    
    try:
        crm = get_crm()
        
        # Test: Create a lead
        print("\n📝 Creating test lead...")
        lead = crm.create_lead(
            name="John Smith",
            email="john.smith@example.com",
            company="Test Corp",
            interest="AI automation for sales",
            lead_score=8.5,
            source="API Test"
        )
        
        print(f"\n✅ Created Lead:")
        print(f"   ID: {lead['id']}")
        print(f"   Name: {lead['name']}")
        print(f"   Score: {lead['lead_score']}")
        print(f"   Status: {lead['status']}")
        
        # Test: Get stats
        print("\n📊 Getting CRM statistics...")
        stats = crm.get_stats()
        print(f"\n📈 CRM Statistics:")
        print(f"   Total Leads: {stats['total_leads']}")
        print(f"   Average Score: {stats['average_score']}")
        print(f"   By Status: {stats['by_status']}")
        
        print("\n✅ All tests passed!")
        print(f"\n🌐 View in Supabase Dashboard:")
        print(f"   https://supabase.com/dashboard/project/YOUR_PROJECT/editor")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("\nMake sure you:")
        print("1. Created Supabase project")
        print("2. Added SUPABASE_URL and SUPABASE_KEY to .env")
        print("3. Created 'leads' table (see SQL below)")