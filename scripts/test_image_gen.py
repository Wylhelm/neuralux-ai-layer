#!/usr/bin/env python3
"""
Test script for NeuroLux image generation feature.

Usage:
    python test_image_gen.py "A beautiful sunset over mountains"
"""

import sys
import httpx
import base64
from pathlib import Path
from datetime import datetime
import argparse


def generate_image(
    prompt: str,
    output_path: str = None,
    width: int = 1024,
    height: int = 1024,
    steps: int = 4,
    model: str = "flux-schnell",
    service_url: str = "http://localhost:8005"
):
    """Generate an image using the vision service."""
    
    print(f"🎨 Generating image with {model}...")
    print(f"📝 Prompt: {prompt}")
    print(f"📐 Size: {width}x{height}")
    print(f"🔢 Steps: {steps}")
    print()
    
    try:
        # Send request to vision service
        print("⏳ Sending request to vision service...")
        response = httpx.post(
            f"{service_url}/v1/generate-image",
            json={
                "prompt": prompt,
                "width": width,
                "height": height,
                "num_inference_steps": steps,
                "model": model,
            },
            timeout=180.0,  # 3 minutes timeout
        )
        response.raise_for_status()
        result = response.json()
        
        # Get image data
        image_b64 = result.get("image_bytes_b64")
        if not image_b64:
            print("❌ Error: No image data returned")
            return False
        
        # Decode image
        print("✅ Image generated successfully!")
        image_bytes = base64.b64decode(image_b64)
        
        # Save to file
        if output_path is None:
            # Generate filename from prompt
            safe_prompt = "".join(c if c.isalnum() or c in " -_" else "" for c in prompt)
            safe_prompt = safe_prompt.replace(" ", "_")[:50]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"generated_{safe_prompt}_{timestamp}.png"
        
        output_file = Path(output_path)
        output_file.write_bytes(image_bytes)
        
        print(f"💾 Image saved to: {output_file.absolute()}")
        print()
        print("📊 Generation info:")
        print(f"  Model: {result.get('model')}")
        print(f"  Size: {result.get('width')}x{result.get('height')}")
        if result.get('seed'):
            print(f"  Seed: {result.get('seed')}")
        
        return True
        
    except httpx.ConnectError:
        print("❌ Error: Could not connect to vision service")
        print("   Make sure the service is running:")
        print("   cd services/vision && python service.py")
        return False
    except httpx.TimeoutException:
        print("❌ Error: Request timed out")
        print("   This might be the first run (downloading models)")
        print("   Try again or check the service logs")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def check_service(service_url: str = "http://localhost:8005"):
    """Check if the vision service is running."""
    try:
        response = httpx.get(f"{service_url}/", timeout=5.0)
        response.raise_for_status()
        data = response.json()
        print("✅ Vision service is running")
        print(f"   Service: {data.get('service')}")
        print(f"   Version: {data.get('version')}")
        print(f"   Status: {data.get('status')}")
        print()
        return True
    except Exception as e:
        print(f"❌ Vision service is not running: {e}")
        print()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Test NeuroLux image generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_image_gen.py "A serene mountain landscape"
  python test_image_gen.py "A cute cat" --size 512x512 --model flux-dev
  python test_image_gen.py "Abstract art" --steps 20 --output art.png
        """
    )
    
    parser.add_argument("prompt", help="Text description of the image to generate")
    parser.add_argument("--output", "-o", help="Output file path (default: auto-generated)")
    parser.add_argument("--size", default="1024x1024", help="Image size (default: 1024x1024)")
    parser.add_argument("--steps", type=int, default=4, help="Number of inference steps (default: 4)")
    parser.add_argument("--model", default="flux-schnell", 
                       choices=["flux-schnell", "flux-dev", "sdxl-lightning"],
                       help="Model to use (default: flux-schnell)")
    parser.add_argument("--url", default="http://localhost:8005", 
                       help="Vision service URL (default: http://localhost:8005)")
    parser.add_argument("--check-only", action="store_true", 
                       help="Only check if service is running")
    
    args = parser.parse_args()
    
    # Banner
    print()
    print("=" * 60)
    print("🎨 NeuroLux Image Generation Test")
    print("=" * 60)
    print()
    
    # Check service
    if not check_service(args.url):
        print("Please start the vision service first:")
        print("  cd services/vision")
        print("  python service.py")
        print()
        sys.exit(1)
    
    if args.check_only:
        print("Service check complete!")
        sys.exit(0)
    
    # Parse size
    try:
        width, height = map(int, args.size.split("x"))
    except:
        print(f"❌ Invalid size format: {args.size}")
        print("   Use format: WIDTHxHEIGHT (e.g., 1024x1024)")
        sys.exit(1)
    
    # Generate image
    success = generate_image(
        prompt=args.prompt,
        output_path=args.output,
        width=width,
        height=height,
        steps=args.steps,
        model=args.model,
        service_url=args.url
    )
    
    if success:
        print()
        print("✨ Success! Your image has been generated.")
        print()
        sys.exit(0)
    else:
        print()
        print("❌ Image generation failed. Check the errors above.")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()

