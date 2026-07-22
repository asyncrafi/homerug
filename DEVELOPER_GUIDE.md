# HomesRug - Developer Guide 🏠🎨

Complete documentation for the HomesRug AI Rug Generation Project.

---

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Setup & Installation](#setup--installation)
5. [Environment Variables](#environment-variables)
6. [API Endpoints](#api-endpoints)
7. [Database Models](#database-models)
8. [Key Features](#key-features)
9. [Development Workflow](#development-workflow)
10. [Docker Deployment](#docker-deployment)
11. [Celery & Async Tasks](#celery--async-tasks)
12. [Integration Points](#integration-points)
13. [Common Issues & Troubleshooting](#common-issues--troubleshooting)

---

## 🎯 Project Overview

**HomesRug** is a Django REST API that allows users to:
- Generate AI-powered custom rug designs using **Google Gemini AI**
- Preview rugs in their rooms using AI photo placement
- Save/favorite multiple rug designs
- Create Shopify checkout directly from generated designs
- Track generation quotas per user email

### Key Workflow:
1. **User generates** → 4 rug design variants (or 2-3) based on style, colors, size, material
2. **User previews** → Uploads room photo, AI places rug in the room
3. **User favorites** → Can favorite any variant (multiple per generation)
4. **User checks out** → Creates draft Shopify product and checkout link

---

## 🛠️ Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Backend** | Django REST Framework | 5.2.1 |
| **Async Tasks** | Celery | 5.5.2 |
| **Task Broker** | Redis | Latest |
| **AI/ML** | Google Gemini API | Latest |
| **Database** | PostgreSQL | (production) / SQLite (dev) |
| **Authentication** | JWT (Simple JWT) | 5.5.1 |
| **API Docs** | drf-spectacular | 0.28.0 |
| **Containerization** | Docker | Latest |
| **Ecommerce** | Shopify API | Latest |
| **File Storage** | Google Cloud Storage | 3.2.0 |
| **Messaging** | django-cors-headers | 4.7.0 |

---

## 📁 Project Structure

```
homesrug/
├── apps/
│   └── ruggen/                    # Main app for rug generation
│       ├── models.py               # Database models
│       ├── views.py                # API views & endpoints
│       ├── serializers.py           # DRF serializers
│       ├── urls.py                 # URL routing
│       ├── tasks.py                # Celery async tasks
│       ├── tests.py                # Unit tests
│       ├── admin.py                # Django admin config
│       ├── migrations/              # Database migrations
│       └── utils/
│           ├── gemini.py            # Google Gemini integration
│           ├── shopify.py           # Shopify API integration
│           ├── pricing.py           # Price calculation logic
│           └── watermark.py         # Watermark utilities
│
├── config/                         # Django project config
│   ├── settings/
│   │   ├── base.py                # Base settings (all envs)
│   │   ├── development.py         # Dev settings
│   │   ├── production.py          # Prod settings
│   │   └── __init__.py
│   ├── urls.py                    # Root URL config
│   ├── wsgi.py                    # WSGI application
│   ├── asgi.py                    # ASGI application (WebSocket)
│   ├── celery.py                  # Celery configuration
│   └── __init__.py
│
├── templates/                      # HTML templates (if any)
├── media/                          # User-uploaded files
├── staticfiles/                    # Collected static files
│
├── manage.py                       # Django CLI
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Docker image definition
├── docker-compose-dev.yml          # Dev environment orchestration
├── docker-compose-prod.yml         # Prod environment orchestration
├── entrypoint.sh                   # Docker startup script
├── .env.example                    # Example environment variables
├── README.md                       # Project overview
└── DEVELOPER_GUIDE.md             # This file
```

---

## 🚀 Setup & Installation

### Local Development Setup

#### 1. **Clone & Enter Project**
```bash
git clone <repo-url>
cd homesrug
```

#### 2. **Create Virtual Environment**
```bash
python3.13 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

#### 4. **Create `.env` File**
Copy `.env.example` to `.env` and fill in all required variables (see [Environment Variables](#environment-variables) section)

#### 5. **Run Migrations**
```bash
python manage.py migrate
```

#### 6. **Create Superuser** (optional, for admin panel)
```bash
python manage.py createsuperuser
```

#### 7. **Start Redis** (for Celery)
```bash
# Using Docker
docker run -d -p 6379:6379 redis:latest

# Or if Redis is installed locally
redis-server
```

#### 8. **Start Celery Worker** (in separate terminal)
```bash
celery -A config worker -l info
```

#### 9. **Start Celery Beat** (for scheduled tasks, optional)
```bash
celery -A config beat -l info
```

#### 10. **Run Development Server**
```bash
python manage.py runserver
```

✅ Server runs at `http://localhost:8000`

---

## 🔐 Environment Variables

Create a `.env` file in the root directory with the following:

```bash
# Django Settings
SECRET_KEY=your-django-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com

# Database (PostgreSQL recommended for production)
DATABASE_URL=postgresql://user:password@localhost:5432/homesrug_db

# Redis (for Celery)
REDIS_URL=redis://localhost:6379/0

# Google Gemini API
GEMINI_API_KEY=your-google-gemini-api-key

# Google Cloud Storage (for file uploads)
GCS_BUCKET_NAME=your-gcs-bucket
GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcs-credentials.json

# Shopify Integration
SHOPIFY_SHOP_URL=https://your-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=your-shopify-access-token

# Email Configuration (optional)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-specific-password
DEFAULT_FROM_EMAIL=noreply@maiahomes.com

# Firebase (if using Firebase Auth)
FIREBASE_CREDENTIALS=/path/to/firebase-credentials.json

# Environment Type
ENVIRONMENT=development  # or 'production'

# Currency
CURRENCY=USD

# Generation Limits
MAX_GENERATIONS=5
```

---

## 📡 API Endpoints

### Base URL
```
http://localhost:8000/api/ruggen/
```

### 1️⃣ **Get Dropdown Options**
```
GET /options/
```
**Response:** Lists all available styles, materials, shapes, colors, pricing info, generation limits

**Query Params:**
- `email` (optional) - Get user-specific limits and quota

---

### 2️⃣ **Generate Rug Designs**
```
POST /generate/
Content-Type: application/json
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "style": "Persian",
  "size": "5x8 feet",
  "material": "Hand Tufted New Zealand Wool",
  "shape": "rectangular",
  "colors": ["navy blue", "cream", "burgundy"],
  "description": "medallion pattern with floral border"
}
```

**Response (202 Accepted):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "status": "pending",
  "created_at": "2026-07-23T10:30:00Z",
  "price": {"amount": 299.99, "currency": "USD"}
}
```

**Status Flow:** `pending` → `generated` (with images) or `failed`

---

### 3️⃣ **Get Generation Detail & Images**
```
GET /<generation_id>/
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "style": "Persian",
  "size": "5x8 feet",
  "material": "Hand Tufted New Zealand Wool",
  "colors": ["navy blue", "cream", "burgundy"],
  "status": "generated",
  "created_at": "2026-07-23T10:30:00Z",
  "rug_images": [
    {
      "index": 0,
      "base64_data": "data:image/jpeg;base64,...",
      "mime_type": "image/jpeg",
      "is_favorite": true
    },
    {
      "index": 1,
      "base64_data": "data:image/jpeg;base64,...",
      "mime_type": "image/jpeg",
      "is_favorite": false
    }
  ],
  "pricing": {"amount": 299.99, "currency": "USD"}
}
```

---

### 4️⃣ **Favorite/Unfavorite Specific Variant**
```
POST /<generation_id>/favorite/
Content-Type: application/json
```

**Request Body:**
```json
{
  "index": 1,
  "is_favorite": true
}
```

**Response (200):**
```json
{
  "generation_id": "550e8400-e29b-41d4-a716-446655440000",
  "index": 1,
  "is_favorite": true,
  "message": "Favorite updated successfully"
}
```

---

### 5️⃣ **Get All Favorites**
```
GET /favorites/?email=user@example.com
```

**Response:**
```json
{
  "count": 5,
  "email": "user@example.com",
  "results": [
    {
      "generation_id": "550e8400-e29b-41d4-a716-446655440000",
      "index": 0,
      "rug_image_id": 142,
      "generation": {
        "style": "Persian",
        "size": "5x8 feet",
        "material": "Hand Tufted New Zealand Wool",
        "shape": "rectangular",
        "colors": ["navy blue", "cream", "burgundy"],
        "created_at": "2026-07-23T10:30:00Z"
      }
    }
  ]
}
```

---

### 6️⃣ **Get User History**
```
GET /history/?email=user@example.com
```

**Response:** Returns all user's past generations + the latest one with details

---

### 7️⃣ **Preview Rug in Room**
```
POST /<generation_id>/preview/
Content-Type: application/json
```

**Request Body:**
```json
{
  "room_image_base64": "data:image/jpeg;base64,...",
  "selected_rug_index": 1
}
```

**Response (202 Accepted):** Returns placement ID and status

---

### 8️⃣ **Create Shopify Checkout**
```
POST /checkout/
Content-Type: application/json
```

**Request Body (Single Item):**
```json
{
  "generation_id": "550e8400-e29b-41d4-a716-446655440000",
  "selected_rug_index": 1,
  "quantity": 1
}
```

**Request Body (Multiple Items):**
```json
{
  "items": [
    {
      "generation_id": "550e8400-e29b-41d4-a716-446655440000",
      "selected_rug_index": 0,
      "quantity": 1
    },
    {
      "generation_id": "550e8400-e29b-41d4-a716-446655440001",
      "selected_rug_index": 2,
      "quantity": 2
    }
  ]
}
```

**Response (200):**
```json
{
  "checkout_url": "https://your-store.myshopify.com/checkout/...",
  "draft_product_id": "123456789"
}
```

---

## 📊 Database Models

### **RugGeneration**
Main model for a generation request.

```python
class RugGeneration(models.Model):
    id = UUIDField(primary_key=True)
    created_at = DateTimeField(auto_now_add=True)
    
    email = EmailField(nullable)
    style = CharField()  # e.g., "Persian", "Moroccan"
    size = CharField()  # e.g., "5x8 feet"
    material = CharField()  # e.g., "Hand Tufted New Zealand Wool"
    shape = CharField()  # "rectangular" or "round"
    colors = JSONField()  # ["navy blue", "cream", "burgundy"]
    description = TextField(blank)
    
    status = CharField(choices=['pending', 'generated', 'failed'])
    error_message = TextField(blank)
```

**Related:** `rug_images` (one-to-many with GeneratedRugImage)

---

### **GeneratedRugImage**
Individual rug variant image from a generation.

```python
class GeneratedRugImage(models.Model):
    generation = ForeignKey(RugGeneration, on_delete=CASCADE)
    index = IntegerField()  # 0, 1, 2, 3, etc.
    base64_data = TextField()
    mime_type = CharField()  # "image/jpeg", "image/png"
    is_favorite = BooleanField(default=False)  # ✨ Can favorite individual variants
```

**Key Point:** Users can favorite ANY combination of variants from the same generation!

---

### **RoomPlacement**
Represents rug placement preview in a room photo.

```python
class RoomPlacement(models.Model):
    id = UUIDField(primary_key=True)
    created_at = DateTimeField(auto_now_add=True)
    
    generation = ForeignKey(RugGeneration, on_delete=CASCADE)
    selected_rug_index = IntegerField()  # Which variant was selected
    
    room_image_base64 = TextField()
    status = CharField(choices=['pending', 'placed', 'failed'])
    result_base64 = TextField(blank)  # Result image with rug placed
    
    # Shopify integration
    shopify_product_id = CharField(blank)
    shopify_variant_id = CharField(blank)
    shopify_image_url = URLField(blank)
    checkout_url = URLField(blank)
```

---

### **GenerationQuota**
Tracks how many generations a user has used.

```python
class GenerationQuota(models.Model):
    email = EmailField(unique)
    count = IntegerField(default=0)  # Number of generations used
    created_at = DateTimeField(auto_now_add=True)
    last_used = DateTimeField(auto_now=True)
```

**Limit:** 5 generations per email (configurable in settings) unless exempt.

---

## ✨ Key Features

### 1. **Multi-Variant Favorites**
- Each generation produces 2-4 variants (configurable)
- User can favorite **any combination** of variants
- Not limited to favoriting entire generations
- Example: From Gen1, favorite index 0+2; from Gen2, favorite only index 3

### 2. **Generation Quota System**
- Track generations per email
- Limit: 5 generations per user (configurable)
- Exempt emails bypass limits (e.g., admin, internal teams)
- Quota increases on successful generation

### 3. **Async Task Processing**
- Image generation runs as background Celery task
- Retry on Gemini API failure (up to 3 retries)
- Non-blocking API responses (HTTP 202 Accepted)
- Poll `GET /<generation_id>/` to check status

### 4. **AI Integration (Google Gemini)**
- Generates custom rug designs based on user parameters
- Supports style, colors, size, material, description
- Watermark applied to all generated images
- Base64 encoded responses

### 5. **Shopify Integration**
- Create draft products on Shopify
- Generate checkout URLs
- Support for single & multi-item checkouts
- Upload images directly to Shopify

### 6. **Dynamic Pricing**
- Calculate price per square foot
- Varies by material
- Rounded up to .99 (e.g., $99.99, $199.99)

---

## 🔄 Development Workflow

### 1. **Adding a New API Endpoint**

**Step 1: Create Serializer** (`serializers.py`)
```python
class MyNewSerializer(serializers.Serializer):
    field1 = serializers.CharField()
    field2 = serializers.IntegerField()
```

**Step 2: Create View** (`views.py`)
```python
class MyNewView(APIView):
    def post(self, request):
        serializer = MyNewSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        # Logic here
        return Response(data, status=status.HTTP_200_OK)
```

**Step 3: Add URL Route** (`urls.py`)
```python
path('mynew/', MyNewView.as_view(), name='my-new'),
```

**Step 4: Test the endpoint**
```bash
curl -X POST http://localhost:8000/api/ruggen/mynew/ \
  -H "Content-Type: application/json" \
  -d '{"field1":"value","field2":123}'
```

---

### 2. **Creating a Database Migration**

```bash
# After modifying a model
python manage.py makemigrations ruggen

# Review the migration file (apps/ruggen/migrations/)
cat apps/ruggen/migrations/0006_auto_xxx.py

# Apply the migration
python manage.py migrate ruggen
```

---

### 3. **Running Tests**

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test apps.ruggen

# Run specific test class
python manage.py test apps.ruggen.tests.RugGenerationTestCase

# With verbose output
python manage.py test -v 2
```

---

### 4. **Debugging with Logs**

**Enable Logging** (add to `.env`):
```bash
DEBUG=True
LOGGING_LEVEL=DEBUG
```

**View Celery Task Logs:**
```bash
celery -A config worker -l debug
```

**Database Query Logs:**
```python
# In settings/development.py
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

---

## 🐳 Docker Deployment

### Development with Docker Compose

```bash
# Start all services (Django, PostgreSQL, Redis, Celery)
docker-compose -f docker-compose-dev.yml up -d

# Stop services
docker-compose -f docker-compose-dev.yml down

# View logs
docker-compose -f docker-compose-dev.yml logs -f django

# Run migrations in Docker
docker-compose -f docker-compose-dev.yml exec django python manage.py migrate
```

### Production Deployment

```bash
# Build production image
docker build -t homesrug:latest .

# Start with production compose
docker-compose -f docker-compose-prod.yml up -d

# View logs
docker-compose -f docker-compose-prod.yml logs -f

# Run management commands
docker exec homesrug_django python manage.py migrate
docker exec homesrug_django python manage.py createsuperuser
```

---

### Docker Entrypoint Flow

The `entrypoint.sh` script automatically:
1. ✅ Runs database migrations (`python manage.py migrate`)
2. ✅ Collects static files (`python manage.py collectstatic --noinput`)
3. ✅ Starts Django development server or Gunicorn (production)

---

## 🔄 Celery & Async Tasks

### Task: Generate Rug Images

**Located:** `apps/ruggen/tasks.py`

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_rug_images_task(self, generation_id, style, colors, ...):
    # Called asynchronously when user generates rugs
    # Retries up to 3 times if Gemini API fails
    # Updates generation status and creates GeneratedRugImage records
```

**Flow:**
1. User calls `POST /generate/` → Returns 202 Accepted with generation ID
2. API queues Celery task with generation parameters
3. Celery worker picks up task, calls Gemini API
4. On success: Creates GeneratedRugImage records, updates quota
5. On failure: Updates status to 'failed', retries if applicable
6. User polls `GET /<generation_id>/` to check status

### Monitoring Celery

```bash
# Start Flower (Celery monitoring UI)
celery -A config flower

# Access at http://localhost:5555
```

---

## 🔗 Integration Points

### **Google Gemini API**
**File:** `apps/ruggen/utils/gemini.py`

```python
def generate_rug_images(style, colors, material, size, description, shape='rectangular'):
    # Sends prompt to Gemini API
    # Returns list of base64 images
```

**Key Configuration:**
- API Key: `GEMINI_API_KEY` (in `.env`)
- Model: `gemini-2.0-flash` (or configured in file)
- Retry logic: Built-in exponential backoff

---

### **Shopify API**
**File:** `apps/ruggen/utils/shopify.py`

**Key Functions:**
- `create_draft_product()` - Creates a draft product on Shopify
- `upload_image_to_shopify()` - Uploads rug image
- `get_checkout_url()` - Generates checkout link
- `get_multi_checkout_url()` - Multi-item checkout

**Configuration:**
- Shop URL: `SHOPIFY_SHOP_URL`
- Access Token: `SHOPIFY_ACCESS_TOKEN`

---

### **Google Cloud Storage**
**For production file storage**

Configuration in `settings/production.py`:
```python
DEFAULT_FILE_STORAGE = 'storages.backends.gcloud_storage.GoogleCloudStorage'
GS_BUCKET_NAME = env('GCS_BUCKET_NAME')
```

---

## 🐛 Common Issues & Troubleshooting

### Issue 1: "Celery task not running"
**Solution:**
```bash
# 1. Verify Redis is running
redis-cli ping  # Should return PONG

# 2. Check Celery worker is started
celery -A config worker -l info

# 3. Check broker URL
# Ensure REDIS_URL is correct in .env
```

---

### Issue 2: "Gemini API rate limit exceeded"
**Solution:**
- Increase `max_retries` in tasks.py
- Implement request throttling
- Add delay between requests
- Check API quota in Google Cloud Console

---

### Issue 3: "Migration conflicts"
**Solution:**
```bash
# Revert last migration
python manage.py migrate ruggen 0005

# Create new migration for changes
python manage.py makemigrations ruggen

# Apply
python manage.py migrate ruggen
```

---

### Issue 4: "Static files not loading"
**Solution:**
```bash
# Collect static files
python manage.py collectstatic --noinput --clear

# Set STATIC_ROOT in settings (if missing)
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'
```

---

### Issue 5: "CORS errors on frontend"
**Solution:**
Check `CORS_ALLOWED_ORIGINS` in `settings/base.py`:
```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Frontend dev
    "https://yourdomain.com",  # Production
]
```

---

### Issue 6: "Database connection refused"
**Solution:**
```bash
# 1. Check DATABASE_URL in .env
# Format: postgresql://user:password@host:port/dbname

# 2. Verify PostgreSQL is running
psql -U postgres -d postgres

# 3. For Docker, ensure services are linked
docker-compose logs postgres  # Check for errors
```

---

## 📚 Useful Commands

```bash
# Django Management
python manage.py shell                    # Interactive Django shell
python manage.py dbshell                  # PostgreSQL shell
python manage.py dumpdata > backup.json   # Backup database
python manage.py loaddata backup.json     # Restore database

# Celery
celery -A config worker -l info           # Start worker
celery -A config beat -l info             # Start beat scheduler
celery -A config purge -f                 # Clear task queue
celery -A config inspect active           # View active tasks

# Database
python manage.py sqlmigrate ruggen 0006   # View SQL for migration
python manage.py showmigrations            # List all migrations
python manage.py migrate --fake-initial    # Mark initial migration as applied

# Testing
python manage.py test apps.ruggen --keepdb # Keep test database
coverage run --source='.' manage.py test   # Code coverage
coverage report                             # View coverage report

# Docker
docker ps                                 # List running containers
docker logs -f <container_id>             # Tail container logs
docker exec -it <container_id> bash       # Enter container shell
```

---

## 🔒 Security Checklist

Before deploying to production:

- [ ] Set `DEBUG=False` in production settings
- [ ] Generate secure `SECRET_KEY` and store in `.env`
- [ ] Set `ALLOWED_HOSTS` to your domain(s)
- [ ] Enable HTTPS (use SSL certificate)
- [ ] Configure CORS properly (whitelist only trusted domains)
- [ ] Set strong database password
- [ ] Use environment variables for all secrets (no hardcoding)
- [ ] Enable CSRF protection on forms
- [ ] Set secure cookie flags in production
- [ ] Use strong Shopify access tokens with minimal permissions
- [ ] Rotate API keys regularly
- [ ] Monitor error logs for suspicious activity

---

## 📞 Support & Questions

For issues or questions:
1. Check logs: `docker logs` or terminal output
2. Review this guide's troubleshooting section
3. Check Django/DRF documentation
4. Contact project maintainer

---

## 📝 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-07-23 | Initial setup, multi-variant favorites, Gemini AI integration |

---

**Happy coding! 🚀** Feel free to update this guide as the project evolves.
