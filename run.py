import argparse
import uvicorn
from app.core.config import settings

def main():
    parser = argparse.ArgumentParser(description="Run the UniLink API server")
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to run the server on (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the server on (default: 8000)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload on code changes (default: based on DEBUG setting)"
    )
    
    args = parser.parse_args()
    
    use_reload = args.reload or settings.DEBUG
    
    if settings.DEBUG:
        print(f"Starting UniLink API in {settings.ENVIRONMENT} mode")
        print(f"Debug mode: enabled")
        print(f"Auto-reload: {'enabled' if use_reload else 'disabled'}")
        print(f"Server running at http://{args.host}:{args.port}")
        print("API documentation available at:")
        print(f"  - Swagger UI: http://{args.host}:{args.port}/docs")
        print(f"  - ReDoc: http://{args.host}:{args.port}/redoc")
    
    try:
        uvicorn.run(
            "app.main:app",
            host=args.host,
            port=args.port,
            reload=use_reload
        )
    except Exception as e:
        print(f"Error starting server: {e}")
        raise

if __name__ == "__main__":
    main() 