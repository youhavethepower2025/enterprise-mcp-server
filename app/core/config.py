from __future__ import annotations

from typing import Optional

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the MCP server."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "MedTainer MCP"
    environment: str = "development"
    version: str = "0.1.0"
    log_level: str = "INFO"

    # Database Settings
    db_host: str = "postgres"
    db_port: int = 5432
    db_name: str = "medtainer"
    db_user: str = "mcp"
    db_password: str = Field(default="mcp_secure_password_change_me", repr=False)
    db_echo: bool = False  # Set to True to see SQL queries

    @computed_field
    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection URL with proper password encoding."""
        from urllib.parse import quote_plus
        encoded_password = quote_plus(self.db_password)
        return f"postgresql://{self.db_user}:{encoded_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    # GoHighLevel
    gohighlevel_base_url: str = "https://rest.gohighlevel.com/v1"
    gohighlevel_api_key: Optional[str] = Field(default=None, repr=False)
    gohighlevel_location_id: Optional[str] = None

    # QuickBooks
    quickbooks_base_url: str = "https://quickbooks.api.intuit.com/v3/company"
    quickbooks_company_id: Optional[str] = None
    quickbooks_access_token: Optional[str] = Field(default=None, repr=False)
    quickbooks_default_customer_id: Optional[str] = None

    # FreshBooks
    freshbooks_base_url: str = "https://api.freshbooks.com/accounting/account"
    freshbooks_account_id: Optional[str] = None
    freshbooks_access_token: Optional[str] = Field(default=None, repr=False)

    # Google Workspace
    google_workspace_project_id: Optional[str] = None
    google_workspace_credentials_path: Optional[str] = None

    # Amazon Seller Central
    amazon_refresh_token: Optional[str] = Field(default=None, repr=False)
    amazon_client_id: Optional[str] = None
    amazon_client_secret: Optional[str] = Field(default=None, repr=False)

    # Cloudflare
    cloudflare_account_id: Optional[str] = None
    cloudflare_api_token: Optional[str] = Field(default=None, repr=False)

    # GoDaddy
    godaddy_api_key: Optional[str] = None
    godaddy_api_secret: Optional[str] = Field(default=None, repr=False)

    # DigitalOcean
    digitalocean_api_token: Optional[str] = Field(default=None, repr=False)

    # MCP Server Authentication
    mcp_api_key: Optional[str] = Field(
        default=None,
        repr=False,
        description="API key for authenticating MCP tool execution requests"
    )


settings = Settings()
