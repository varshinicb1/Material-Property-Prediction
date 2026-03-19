"""Model versioning and metadata management.

Tracks model versions, training metadata, and enables model rollback.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import hashlib


@dataclass
class ModelMetadata:
    """Metadata for a trained model."""
    
    version: str
    timestamp: str
    config: dict[str, Any]
    metrics: dict[str, Any]
    git_commit: Optional[str] = None
    python_version: Optional[str] = None
    dependencies: Optional[dict[str, str]] = None
    training_duration_seconds: Optional[float] = None
    dataset_hash: Optional[str] = None


class ModelVersionManager:
    """Manages model versions and metadata."""
    
    def __init__(self, models_dir: str = "models"):
        """Initialize version manager.
        
        Args:
            models_dir: Base directory for models.
        """
        self.models_dir = Path(models_dir)
        self.versions_dir = self.models_dir / "versions"
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        
        self.metadata_file = self.models_dir / "metadata.json"
        self.metadata: dict[str, ModelMetadata] = self._load_metadata()
    
    def _load_metadata(self) -> dict[str, ModelMetadata]:
        """Load metadata from file."""
        if not self.metadata_file.exists():
            return {}
        
        with open(self.metadata_file) as f:
            data = json.load(f)
        
        return {
            version: ModelMetadata(**meta)
            for version, meta in data.items()
        }
    
    def _save_metadata(self) -> None:
        """Save metadata to file."""
        data = {
            version: asdict(meta)
            for version, meta in self.metadata.items()
        }
        
        with open(self.metadata_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def create_version(
        self,
        source_dir: str,
        config: dict[str, Any],
        metrics: dict[str, Any],
        version: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Create a new model version.
        
        Args:
            source_dir: Directory containing trained models.
            config: Training configuration.
            metrics: Training metrics.
            version: Optional version string. If None, uses timestamp.
            **kwargs: Additional metadata fields.
            
        Returns:
            Version string.
        """
        if version is None:
            version = datetime.now().strftime("v%Y%m%d_%H%M%S")
        
        # Create version directory
        version_dir = self.versions_dir / version
        version_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy model files
        source_path = Path(source_dir)
        for file in source_path.glob("*"):
            if file.is_file():
                shutil.copy2(file, version_dir / file.name)
        
        # Create metadata
        metadata = ModelMetadata(
            version=version,
            timestamp=datetime.now().isoformat(),
            config=config,
            metrics=metrics,
            **kwargs,
        )
        
        self.metadata[version] = metadata
        self._save_metadata()
        
        # Update 'latest' symlink
        latest_link = self.models_dir / "latest"
        if latest_link.exists() or latest_link.is_symlink():
            latest_link.unlink()
        
        try:
            latest_link.symlink_to(version_dir, target_is_directory=True)
        except OSError:
            # Symlinks may not work on Windows, copy instead
            if latest_link.exists():
                shutil.rmtree(latest_link)
            shutil.copytree(version_dir, latest_link)
        
        return version
    
    def get_version(self, version: str) -> Optional[Path]:
        """Get path to a specific version.
        
        Args:
            version: Version string.
            
        Returns:
            Path to version directory or None if not found.
        """
        version_dir = self.versions_dir / version
        return version_dir if version_dir.exists() else None
    
    def get_latest_version(self) -> Optional[str]:
        """Get the latest version string.
        
        Returns:
            Latest version string or None.
        """
        if not self.metadata:
            return None
        
        return max(
            self.metadata.keys(),
            key=lambda v: self.metadata[v].timestamp,
        )
    
    def list_versions(self) -> list[str]:
        """List all available versions.
        
        Returns:
            List of version strings, sorted by timestamp.
        """
        return sorted(
            self.metadata.keys(),
            key=lambda v: self.metadata[v].timestamp,
            reverse=True,
        )
    
    def get_metadata(self, version: str) -> Optional[ModelMetadata]:
        """Get metadata for a specific version.
        
        Args:
            version: Version string.
            
        Returns:
            ModelMetadata or None if not found.
        """
        return self.metadata.get(version)
    
    def rollback_to_version(self, version: str) -> bool:
        """Rollback to a specific version.
        
        Args:
            version: Version to rollback to.
            
        Returns:
            True if successful, False otherwise.
        """
        version_dir = self.get_version(version)
        if version_dir is None:
            return False
        
        # Update saved directory
        saved_dir = self.models_dir / "saved"
        if saved_dir.exists():
            shutil.rmtree(saved_dir)
        
        shutil.copytree(version_dir, saved_dir)
        return True
    
    def compute_dataset_hash(self, data_dir: str) -> str:
        """Compute hash of dataset for reproducibility.
        
        Args:
            data_dir: Directory containing dataset files.
            
        Returns:
            SHA256 hash of dataset.
        """
        hasher = hashlib.sha256()
        
        for file in sorted(Path(data_dir).glob("*.parquet")):
            with open(file, "rb") as f:
                hasher.update(f.read())
        
        return hasher.hexdigest()[:16]
