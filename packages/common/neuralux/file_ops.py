"""File operations and path utilities for conversational workflows."""

import os
import shutil
from pathlib import Path
from typing import Optional, Tuple
import structlog

logger = structlog.get_logger(__name__)


class PathExpander:
    """Expand and resolve paths for user convenience."""
    
    # Common folder shortcuts
    SHORTCUTS = {
        "desktop": "~/Desktop",
        "documents": "~/Documents",
        "downloads": "~/Downloads",
        "pictures": "~/Pictures",
        "music": "~/Music",
        "videos": "~/Videos",
        "home": "~",
    }
    
    @staticmethod
    def expand(path: str, working_directory: Optional[str] = None) -> Path:
        """
        Expand a path with support for:
        - ~ (home directory)
        - Environment variables ($VAR)
        - Relative paths (relative to working_directory)
        - Shortcuts like 'Desktop', 'Pictures'
        
        Args:
            path: Path to expand
            working_directory: Base directory for relative paths
            
        Returns:
            Expanded absolute Path
        """
        if not path:
            return Path.home()
        
        # Check for shortcuts first
        path_lower = path.lower()
        for shortcut, target in PathExpander.SHORTCUTS.items():
            if path_lower == shortcut or path_lower.startswith(f"{shortcut}/"):
                # Replace shortcut with target
                path = path.replace(shortcut, target, 1).replace(shortcut.capitalize(), target, 1)
                break
        
        # Expand ~ and environment variables
        path = os.path.expanduser(path)
        path = os.path.expandvars(path)
        
        p = Path(path)
        
        # Make absolute
        if not p.is_absolute():
            if working_directory:
                p = Path(working_directory) / p
            else:
                p = Path.cwd() / p
        
        # Resolve to absolute path (follow symlinks)
        try:
            p = p.resolve()
        except Exception:
            # If resolution fails, at least make it absolute
            p = p.absolute()
        
        return p
    
    @staticmethod
    def validate_write_path(path: Path, create_parents: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Validate that a path is safe and writable.
        
        Returns:
            (is_valid, error_message)
        """
        try:
            # Check if path is under home directory (safety check)
            home = Path.home()
            try:
                path.relative_to(home)
            except ValueError:
                # Not under home - warn but allow (user may have other write locations)
                logger.warning("path_outside_home", path=str(path))
            
            # Check if parent exists or can be created
            parent = path.parent
            if not parent.exists():
                if create_parents:
                    try:
                        parent.mkdir(parents=True, exist_ok=True)
                        logger.info("created_parent_directories", path=str(parent))
                    except Exception as e:
                        return False, f"Cannot create parent directories: {e}"
                else:
                    return False, f"Parent directory does not exist: {parent}"
            
            # Check if parent is writable
            if not os.access(parent, os.W_OK):
                return False, f"Parent directory is not writable: {parent}"
            
            # If file exists, check if it's writable
            if path.exists() and not os.access(path, os.W_OK):
                return False, f"File exists and is not writable: {path}"
            
            return True, None
            
        except Exception as e:
            return False, f"Path validation error: {e}"


class FileOperations:
    """Safe file operations for conversational workflows."""
    
    @staticmethod
    def create_file(path: Path, content: str = "", overwrite: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Create a file with optional content.
        
        Returns:
            (success, error_message)
        """
        try:
            # Validate path
            is_valid, error = PathExpander.validate_write_path(path, create_parents=True)
            if not is_valid:
                return False, error
            
            # Check if file exists
            if path.exists() and not overwrite:
                return False, f"File already exists: {path}"
            
            # Write file
            path.write_text(content, encoding="utf-8")
            logger.info("file_created", path=str(path), size=len(content))
            return True, None
            
        except Exception as e:
            logger.error("file_create_failed", path=str(path), error=str(e))
            return False, f"Failed to create file: {e}"
    
    @staticmethod
    def write_file(path: Path, content: str, mode: str = "w") -> Tuple[bool, Optional[str]]:
        """
        Write content to a file.
        
        Args:
            path: File path
            content: Content to write
            mode: Write mode ('w' for overwrite, 'a' for append)
            
        Returns:
            (success, error_message)
        """
        try:
            # Validate path
            is_valid, error = PathExpander.validate_write_path(path, create_parents=True)
            if not is_valid:
                return False, error
            
            # Write file
            if mode == "a":
                # Append mode
                with path.open("a", encoding="utf-8") as f:
                    f.write(content)
                logger.info("file_appended", path=str(path), size=len(content))
            else:
                # Overwrite mode
                path.write_text(content, encoding="utf-8")
                logger.info("file_written", path=str(path), size=len(content))
            
            return True, None
            
        except Exception as e:
            logger.error("file_write_failed", path=str(path), error=str(e))
            return False, f"Failed to write file: {e}"
    
    @staticmethod
    def read_file(path: Path, max_size: int = 10 * 1024 * 1024) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Read file content.
        
        Args:
            path: File path
            max_size: Maximum file size to read (default 10MB)
            
        Returns:
            (success, content, error_message)
        """
        try:
            # Check if file exists
            if not path.exists():
                return False, None, f"File does not exist: {path}"
            
            # Check file size
            size = path.stat().st_size
            if size > max_size:
                return False, None, f"File too large: {size} bytes (max {max_size})"
            
            # Read file
            content = path.read_text(encoding="utf-8")
            logger.info("file_read", path=str(path), size=size)
            return True, content, None
            
        except Exception as e:
            logger.error("file_read_failed", path=str(path), error=str(e))
            return False, None, f"Failed to read file: {e}"
    
    @staticmethod
    def move_file(src: Path, dst: Path, overwrite: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Move or rename a file.
        
        Returns:
            (success, error_message)
        """
        try:
            # Check source exists
            if not src.exists():
                return False, f"Source file does not exist: {src}"
            
            # Validate destination
            is_valid, error = PathExpander.validate_write_path(dst, create_parents=True)
            if not is_valid:
                return False, error
            
            # Check if destination exists
            if dst.exists() and not overwrite:
                return False, f"Destination file already exists: {dst}"
            
            # Move file
            shutil.move(str(src), str(dst))
            logger.info("file_moved", src=str(src), dst=str(dst))
            return True, None
            
        except Exception as e:
            logger.error("file_move_failed", src=str(src), dst=str(dst), error=str(e))
            return False, f"Failed to move file: {e}"
    
    @staticmethod
    def copy_file(src: Path, dst: Path, overwrite: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Copy a file.
        
        Returns:
            (success, error_message)
        """
        try:
            # Check source exists
            if not src.exists():
                return False, f"Source file does not exist: {src}"
            
            # Validate destination
            is_valid, error = PathExpander.validate_write_path(dst, create_parents=True)
            if not is_valid:
                return False, error
            
            # Check if destination exists
            if dst.exists() and not overwrite:
                return False, f"Destination file already exists: {dst}"
            
            # Copy file
            shutil.copy2(str(src), str(dst))
            logger.info("file_copied", src=str(src), dst=str(dst))
            return True, None
            
        except Exception as e:
            logger.error("file_copy_failed", src=str(src), dst=str(dst), error=str(e))
            return False, f"Failed to copy file: {e}"
    
    @staticmethod
    def delete_file(path: Path) -> Tuple[bool, Optional[str]]:
        """
        Delete a file.
        
        Returns:
            (success, error_message)
        """
        try:
            if not path.exists():
                return False, f"File does not exist: {path}"
            
            path.unlink()
            logger.info("file_deleted", path=str(path))
            return True, None
            
        except Exception as e:
            logger.error("file_delete_failed", path=str(path), error=str(e))
            return False, f"Failed to delete file: {e}"
    
    @staticmethod
    def list_directory(path: Path) -> Tuple[bool, Optional[list], Optional[str]]:
        """
        List files in a directory.
        
        Returns:
            (success, file_list, error_message)
        """
        try:
            if not path.exists():
                return False, None, f"Directory does not exist: {path}"
            
            if not path.is_dir():
                return False, None, f"Not a directory: {path}"
            
            files = [str(f) for f in path.iterdir()]
            logger.info("directory_listed", path=str(path), count=len(files))
            return True, files, None
            
        except Exception as e:
            logger.error("directory_list_failed", path=str(path), error=str(e))
            return False, None, f"Failed to list directory: {e}"

