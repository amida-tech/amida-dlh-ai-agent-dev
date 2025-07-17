# Amida AI Ticket Orchestrator - Backend

A FastAPI-based backend for the Amida AI Ticket Orchestrator system. This backend provides a robust ticket management system with AI processing capabilities, real-time updates, and enterprise-grade features.

## Features

- **Ticket Management**: Create, update, track, and manage AI-powered tickets
- **AI Integration**: Azure OpenAI (Grok 3) integration for intelligent task processing
- **Real-time Updates**: WebSocket support for live ticket status updates
- **Async Processing**: Celery task queue for background AI processing
- **MCP Integration**: Model Context Protocol support for Snowflake operations
- **Authentication**: JWT-based authentication with role-based access control
- **File Processing**: Support for various file formats (PDF, DOCX, text files)
- **Audit Logging**: Comprehensive audit trail for all operations
- **Docker Support**: Full containerization for easy deployment

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 12+
- Redis 6+
- Docker & Docker Compose (optional)

### Local Development

1. **Clone and setup**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your actual configuration
   ```

3. **Setup database**:
   ```bash
   python scripts/setup.py
   ```

4. **Start development server**:
   ```bash
   python scripts/start-dev.py
   ```

   Or manually:
   ```bash
   # Terminal 1: FastAPI server
   uvicorn main:app --reload

   # Terminal 2: Celery worker
   celery -A app.tasks.celery_app worker --loglevel=info
   ```

### Docker Development

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get JWT token
- `POST /api/v1/auth/login/json` - Login with JSON payload

### Users
- `GET /api/v1/users/me` - Get current user profile
- `PUT /api/v1/users/me` - Update current user profile
- `GET /api/v1/users/` - List all users (admin only)
- `POST /api/v1/users/` - Create user (admin only)

### Tickets
- `POST /api/v1/tickets/` - Create new ticket
- `GET /api/v1/tickets/` - List tickets with filtering
- `GET /api/v1/tickets/{id}` - Get specific ticket
- `PUT /api/v1/tickets/{id}` - Update ticket
- `DELETE /api/v1/tickets/{id}` - Delete ticket
- `POST /api/v1/tickets/{id}/attachments` - Upload file attachment
- `POST /api/v1/tickets/{id}/reprocess` - Reprocess failed ticket

### WebSocket
- `WS /api/v1/ws/ws/{token}` - Real-time updates connection

## Task Types

The system supports the following predefined task types:

### 1. PR Review (`pr_review`)
- Analyzes GitHub pull requests
- Provides code quality feedback
- Identifies security issues and bugs
- Suggests improvements

**Task Data Example**:
```json
{
  "pr_url": "https://github.com/owner/repo/pull/123",
  "additional_instructions": "Focus on security vulnerabilities"
}
```

### 2. Document Analysis (`doc_analysis`)
- Processes uploaded documents (PDF, DOCX, text)
- Extracts key insights and information
- Provides summaries and recommendations

**Task Data Example**:
```json
{
  "analysis_type": "technical_review",
  "instructions": "Extract technical requirements and identify gaps"
}
```

### 3. Paper Writing (`paper_writing`)
- Generates reports, papers, and documentation
- Supports various content types and audiences
- Customizable length and style

**Task Data Example**:
```json
{
  "topic": "AI Integration Best Practices",
  "paper_type": "technical_report",
  "target_audience": "software_engineers",
  "length": "medium",
  "requirements": "Include code examples and case studies"
}
```

### 4. Snowflake Query (`snowflake_query`)
- Natural language to SQL conversion
- Data analysis and insights
- Uses MCP integration for Snowflake Cortex

**Task Data Example**:
```json
{
  "query_request": "Show me sales trends for the last quarter by region"
}
```

### 5. Custom Tasks (`custom`)
- Flexible task type for organization-specific needs
- Fully customizable prompts and processing

**Task Data Example**:
```json
{
  "task_description": "Generate test cases for the user authentication module",
  "instructions": "Include both positive and negative test scenarios",
  "context": "Web application with JWT authentication"
}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | Required |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint | Required |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | Required |
| `SECRET_KEY` | JWT secret key | Required |
| `ALLOWED_ORIGINS` | CORS allowed origins | localhost:3000,localhost:5173 |
| `MAX_FILE_SIZE` | Maximum file upload size (bytes) | 10485760 (10MB) |

### Azure OpenAI Setup

1. Create an Azure OpenAI resource
2. Deploy a Grok 3 model
3. Configure the endpoint and API key in your `.env` file

### Snowflake MCP Setup

1. Install the Snowflake MCP server:
   ```bash
   # This would be the actual MCP installation
   # npm install -g @snowflake-labs/mcp-server
   ```

2. Configure your Snowflake connection in `.env`:
   ```bash
   SNOWFLAKE_ACCOUNT=your-account
   SNOWFLAKE_USER=your-username
   SNOWFLAKE_PASSWORD=your-password
   SNOWFLAKE_DATABASE=your-database
   ```

## Development

### Project Structure

```
backend/
├── app/
│   ├── api/v1/endpoints/     # API route handlers
│   ├── core/                 # Configuration and settings
│   ├── db/                   # Database setup and session management
│   ├── models/               # SQLAlchemy models
│   ├── schemas/              # Pydantic schemas
│   ├── services/             # Business logic and external integrations
│   └── tasks/                # Celery tasks
├── migrations/               # Alembic database migrations
├── mcp/                      # MCP configuration
├── scripts/                  # Utility scripts
├── uploads/                  # File upload directory
├── requirements.txt          # Python dependencies
├── docker-compose.yml        # Docker services
└── main.py                   # FastAPI application entry point
```

### Adding New Task Types

1. **Add to TaskType enum** in `app/models/ticket.py`:
   ```python
   class TaskType(str, enum.Enum):
       NEW_TASK = "new_task"
   ```

2. **Create processor function** in `app/tasks/ai_orchestrator.py`:
   ```python
   async def process_new_task(ticket: Ticket, ai_client: AzureAIClient, db: AsyncSession):
       # Implementation here
       pass
   ```

3. **Add to main processor** in `ai_orchestrator.py`:
   ```python
   elif ticket.task_type == TaskType.NEW_TASK:
       result = await process_new_task(ticket, ai_client, db)
   ```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Downgrade
alembic downgrade -1
```

### Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest

# Run with coverage
pytest --cov=app tests/
```

### Code Quality

```bash
# Format code
black .

# Sort imports
isort .

# Lint
flake8
```

## Monitoring and Debugging

### Celery Monitoring

Access Flower (Celery monitoring) at `http://localhost:5555` when running with Docker Compose.

### Logs

- Application logs: Check Docker Compose logs or console output
- Celery task logs: Monitor Celery worker output
- Database logs: Check PostgreSQL logs for query performance

### Common Issues

1. **Database connection errors**: Ensure PostgreSQL is running and credentials are correct
2. **Redis connection errors**: Ensure Redis is running and accessible
3. **Azure OpenAI errors**: Check API key and endpoint configuration
4. **File upload errors**: Check upload directory permissions and file size limits

## Deployment

### Production Environment

1. **Environment Configuration**:
   - Use strong SECRET_KEY
   - Configure production database
   - Set DEBUG=false
   - Configure proper CORS origins

2. **Azure Deployment**:
   - Use Azure App Service for the backend
   - Azure Database for PostgreSQL for the database
   - Azure Cache for Redis for caching
   - Azure Storage for file uploads

3. **Security Considerations**:
   - Use HTTPS in production
   - Configure firewall rules
   - Enable database SSL
   - Regular security updates

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

[Your License Here]

## Support

For issues and questions, please create an issue in the GitHub repository or contact the development team.