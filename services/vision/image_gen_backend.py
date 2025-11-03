"""Image generation backend with Flux model support."""

import time
import torch
import structlog
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from PIL import Image
import gc
import os

logger = structlog.get_logger(__name__)

# Global progress callback for model downloads
_download_progress_callback: Optional[Callable[[str], None]] = None

def set_download_progress_callback(callback: Optional[Callable[[str], None]]):
    """Set a callback for download progress updates."""
    global _download_progress_callback
    _download_progress_callback = callback

def _log_progress(message: str):
    """Log progress message."""
    logger.info(message)
    if _download_progress_callback:
        try:
            _download_progress_callback(message)
        except Exception as e:
            logger.error("Progress callback failed", error=str(e))


class ImageGenerationBackend:
    """Backend for image generation using Flux and other diffusion models."""
    
    def __init__(self):
        """Initialize the image generation backend."""
        self.pipeline = None
        self.current_model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._last_used: float = 0.0  # Track last usage time
        self._unload_timeout: int = 300  # Unload after 5 minutes of inactivity
        logger.info("Image generation backend initialized", device=self.device)
    
    def load_model(self, model_name: str = "flux-schnell") -> None:
        """Load a specific model.
        
        Args:
            model_name: Name of the model to load. Options:
                - flux-schnell: FLUX.1-schnell (fast, 4-step)
                - flux-dev: FLUX.1-dev (higher quality, slower)
                - sdxl-lightning: SDXL-Lightning (4-step, faster)
        """
        try:
            # Unload current model if any
            if self.pipeline is not None:
                self.unload_model()
            
            _log_progress(f"Loading {model_name} model...")
            logger.info("Loading image generation model", model=model_name)
            
            # Check if model is already cached
            cache_dir = os.path.expanduser(os.getenv("HF_HOME", "~/.cache/huggingface"))
            
            if model_name == "flux-schnell":
                # Use 8-bit quantized version to save memory (~12GB instead of ~20GB)
                model_id = "black-forest-labs/FLUX.1-schnell"
                _log_progress("Checking for cached Flux Schnell model...")
                
                from diffusers import FluxPipeline, BitsAndBytesConfig
                _log_progress("Loading 8-bit quantized Flux Schnell (~12 GB VRAM)...")
                _log_progress("This may take 10-30 minutes on first download...")
                
                # Configure 8-bit quantization
                quantization_config = BitsAndBytesConfig(
                    load_in_8bit=True,
                    bnb_8bit_compute_dtype=torch.bfloat16
                )
                
                try:
                    self.pipeline = FluxPipeline.from_pretrained(
                        model_id,
                        quantization_config=quantization_config,
                        torch_dtype=torch.bfloat16 if self.device == "cuda" else torch.float32,
                        low_cpu_mem_usage=True,
                    )
                except Exception as e:
                    # Fallback to standard loading if quantization fails
                    _log_progress("8-bit loading failed, trying CPU offload...")
                    self.pipeline = FluxPipeline.from_pretrained(
                        model_id,
                        torch_dtype=torch.bfloat16 if self.device == "cuda" else torch.float32,
                        low_cpu_mem_usage=True,
                    )
                
                _log_progress("Model loaded. Configuring memory management...")
                # Enable aggressive memory savings
                self.pipeline.enable_model_cpu_offload()  # Save VRAM
                self.pipeline.enable_sequential_cpu_offload()  # Even more aggressive
                if hasattr(self.pipeline, 'enable_vae_slicing'):
                    self.pipeline.enable_vae_slicing()  # Reduce VAE memory
                if hasattr(self.pipeline, 'enable_vae_tiling'):
                    self.pipeline.enable_vae_tiling()  # Further reduce VAE memory
                
            elif model_name == "flux-dev":
                model_id = "black-forest-labs/FLUX.1-dev"
                _log_progress("Checking for cached Flux Dev model...")
                
                from diffusers import FluxPipeline
                _log_progress("Downloading Flux Dev model (if needed, ~12 GB)...")
                _log_progress("This may take 10-30 minutes on first run...")
                
                self.pipeline = FluxPipeline.from_pretrained(
                    model_id,
                    torch_dtype=torch.bfloat16 if self.device == "cuda" else torch.float32
                )
                _log_progress("Model downloaded. Configuring memory management...")
                # Enable aggressive memory savings
                self.pipeline.enable_model_cpu_offload()  # Save VRAM
                self.pipeline.enable_sequential_cpu_offload()  # Even more aggressive
                if hasattr(self.pipeline, 'enable_vae_slicing'):
                    self.pipeline.enable_vae_slicing()  # Reduce VAE memory
                if hasattr(self.pipeline, 'enable_vae_tiling'):
                    self.pipeline.enable_vae_tiling()  # Further reduce VAE memory
                
            elif model_name == "sdxl-lightning":
                model_id = "ByteDance/SDXL-Lightning"
                _log_progress("Checking for cached SDXL Lightning model...")
                
                from diffusers import StableDiffusionXLPipeline, EulerDiscreteScheduler
                _log_progress("Downloading SDXL Lightning model (if needed, ~7 GB)...")
                
                self.pipeline = StableDiffusionXLPipeline.from_pretrained(
                    model_id,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    variant="fp16" if self.device == "cuda" else None
                )
                _log_progress("Model downloaded. Configuring scheduler...")
                self.pipeline.scheduler = EulerDiscreteScheduler.from_config(
                    self.pipeline.scheduler.config,
                    timestep_spacing="trailing"
                )
                if self.device == "cuda":
                    _log_progress("Moving model to GPU...")
                    self.pipeline.to(self.device)
            else:
                raise ValueError(f"Unknown model: {model_name}")
            
            self.current_model = model_name
            self._last_used = time.time()  # Update usage time when loading
            _log_progress(f"✓ {model_name} ready!")
            logger.info("Model loaded successfully", model=model_name)
            
        except Exception as e:
            error_msg = f"Failed to load model: {str(e)}"
            _log_progress(error_msg)
            logger.error("Failed to load image generation model", model=model_name, error=str(e))
            raise
    
    def should_unload(self) -> bool:
        """Check if model should be unloaded due to inactivity."""
        if self.pipeline is None:
            return False
        if self._last_used == 0.0:
            return False
        inactive_time = time.time() - self._last_used
        return inactive_time > self._unload_timeout
    
    def unload_model(self) -> None:
        """Unload the current model and free VRAM."""
        if self.pipeline is not None:
            logger.info("Unloading image generation model", model=self.current_model)
            del self.pipeline
            self.pipeline = None
            self.current_model = None
            self._last_used = 0.0
            
            # Force garbage collection and clear CUDA cache
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
    
    def generate(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        num_inference_steps: int = 4,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None,
    ) -> Image.Image:
        """Generate an image from a text prompt.
        
        Args:
            prompt: Text description of the image to generate
            negative_prompt: What to avoid in the image
            width: Image width (default 1024)
            height: Image height (default 1024)
            num_inference_steps: Number of denoising steps (4 for fast models, 20-50 for quality)
            guidance_scale: How closely to follow the prompt (7.5 is balanced)
            seed: Random seed for reproducibility
            
        Returns:
            Generated PIL Image
        """
        if self.pipeline is None:
            _log_progress("No model loaded, loading default flux-schnell...")
            logger.info("No model loaded, loading default flux-schnell")
            self.load_model("flux-schnell")
        self._last_used = time.time()  # Update usage time
        
        try:
            _log_progress(f"Generating {width}x{height} image ({num_inference_steps} steps)...")
            logger.info(
                "Generating image",
                prompt=prompt[:50] + "..." if len(prompt) > 50 else prompt,
                size=f"{width}x{height}",
                steps=num_inference_steps
            )
            
            # Set random seed if provided
            generator = None
            if seed is not None:
                generator = torch.Generator(device=self.device).manual_seed(seed)
            
            # Adjust parameters based on model
            kwargs: Dict[str, Any] = {
                "prompt": prompt,
                "width": width,
                "height": height,
                "num_inference_steps": num_inference_steps,
                "generator": generator,
            }
            
            # Flux models handle guidance differently
            if "flux" in self.current_model:
                # Flux uses guidance_scale differently or not at all for schnell
                if self.current_model == "flux-dev":
                    kwargs["guidance_scale"] = guidance_scale
                # flux-schnell doesn't use guidance_scale (distilled model)
            else:
                kwargs["guidance_scale"] = guidance_scale
                
            if negative_prompt:
                kwargs["negative_prompt"] = negative_prompt
            
            # Generate image
            _log_progress("Running diffusion process...")
            result = self.pipeline(**kwargs)
            image = result.images[0]
            
            _log_progress("✓ Image generated successfully!")
            logger.info("Image generated successfully")
            return image
            
        except Exception as e:
            logger.error("Image generation failed", error=str(e))
            raise
    
    def is_loaded(self) -> bool:
        """Check if a model is currently loaded."""
        return self.pipeline is not None
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        return {
            "loaded": self.is_loaded(),
            "model": self.current_model,
            "device": self.device,
            "cuda_available": torch.cuda.is_available(),
        }

