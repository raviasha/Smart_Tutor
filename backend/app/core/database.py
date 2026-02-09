from supabase import create_client, Client
from app.core.config import settings

# Supabase client using service role key (server-side, full access)
supabase: Client = create_client(
    settings.supabase_url,
    settings.supabase_service_role_key,
)


def get_supabase() -> Client:
    """Dependency that provides the Supabase client."""
    return supabase
