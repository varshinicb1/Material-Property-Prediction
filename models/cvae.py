"""Conditional Variational Autoencoder (CVAE) for stress-strain curve generation.

The CVAE learns a conditional distribution p(curve | features) where features
are welding parameters, HAZ descriptors, and repair stage. During inference,
latent samples are drawn and decoded to produce full stress-strain curves.

Physics-aware constraints:
  - Monotonic strain axis (enforced by construction)
  - Smooth stress response (smoothness regularization loss)
  - Yield < UTS (soft constraint in loss)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from utils.logging import get_logger

logger = get_logger(__name__)


class Encoder(nn.Module):
    """CVAE encoder: q(z | x_curve, x_features)."""

    def __init__(
        self,
        curve_dim: int,
        condition_dim: int,
        hidden_dims: list[int],
        latent_dim: int,
    ) -> None:
        super().__init__()
        input_dim = curve_dim + condition_dim
        layers: list[nn.Module] = []
        prev = input_dim
        for h in hidden_dims:
            layers += [nn.Linear(prev, h), nn.LayerNorm(h), nn.GELU()]
            prev = h
        self.network = nn.Sequential(*layers)
        self.mu_head = nn.Linear(prev, latent_dim)
        self.logvar_head = nn.Linear(prev, latent_dim)

    def forward(
        self, curve: torch.Tensor, condition: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Encode curve+condition to latent parameters.

        Args:
            curve: Stress curve tensor, shape (B, curve_dim).
            condition: Condition embedding, shape (B, condition_dim).

        Returns:
            Tuple of (mu, log_var) each of shape (B, latent_dim).
        """
        x = torch.cat([curve, condition], dim=-1)
        h = self.network(x)
        return self.mu_head(h), self.logvar_head(h)


class Decoder(nn.Module):
    """CVAE decoder: p(x_curve | z, x_features)."""

    def __init__(
        self,
        latent_dim: int,
        condition_dim: int,
        hidden_dims: list[int],
        curve_dim: int,
    ) -> None:
        super().__init__()
        input_dim = latent_dim + condition_dim
        layers: list[nn.Module] = []
        prev = input_dim
        for h in hidden_dims:
            layers += [nn.Linear(prev, h), nn.LayerNorm(h), nn.GELU()]
            prev = h
        self.network = nn.Sequential(*layers)
        self.out_head = nn.Linear(prev, curve_dim)

    def forward(self, z: torch.Tensor, condition: torch.Tensor) -> torch.Tensor:
        """Decode latent vector to stress curve.

        Args:
            z: Latent tensor, shape (B, latent_dim).
            condition: Condition embedding, shape (B, condition_dim).

        Returns:
            Reconstructed stress curve, shape (B, curve_dim).
        """
        x = torch.cat([z, condition], dim=-1)
        h = self.network(x)
        return self.out_head(h)


class ConditionEncoder(nn.Module):
    """Encode raw input features to a fixed-size condition embedding."""

    def __init__(self, n_features: int, condition_dim: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_features, condition_dim * 2),
            nn.LayerNorm(condition_dim * 2),
            nn.GELU(),
            nn.Linear(condition_dim * 2, condition_dim),
            nn.LayerNorm(condition_dim),
            nn.GELU(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class CVAE(nn.Module):
    """Conditional VAE for stress-strain curve generation.

    Attributes:
        condition_encoder: Maps input features to condition embedding.
        encoder: Maps (curve, condition) to latent (mu, logvar).
        decoder: Maps (z, condition) to reconstructed curve.
    """

    def __init__(
        self,
        n_features: int,
        curve_dim: int = 50,
        latent_dim: int = 32,
        condition_dim: int = 64,
        encoder_hidden: list[int] | None = None,
        decoder_hidden: list[int] | None = None,
    ) -> None:
        """Initialize CVAE.

        Args:
            n_features: Number of input conditioning features.
            curve_dim: Length of stress-strain curve vector.
            latent_dim: Dimensionality of latent space.
            condition_dim: Dimensionality of condition embedding.
            encoder_hidden: Hidden layer sizes for encoder.
            decoder_hidden: Hidden layer sizes for decoder.
        """
        super().__init__()
        if encoder_hidden is None:
            encoder_hidden = [256, 128]
        if decoder_hidden is None:
            decoder_hidden = [128, 256]

        self.curve_dim = curve_dim
        self.latent_dim = latent_dim

        self.condition_encoder = ConditionEncoder(n_features, condition_dim)
        self.encoder = Encoder(curve_dim, condition_dim, encoder_hidden, latent_dim)
        self.decoder = Decoder(latent_dim, condition_dim, decoder_hidden, curve_dim)

    def reparameterize(self, mu: torch.Tensor, log_var: torch.Tensor) -> torch.Tensor:
        """Reparameterization trick: z = mu + eps * std.

        Args:
            mu: Mean of latent distribution.
            log_var: Log variance of latent distribution.

        Returns:
            Sampled latent vector.
        """
        if self.training:
            std = torch.exp(0.5 * log_var)
            eps = torch.randn_like(std)
            return mu + eps * std
        return mu

    def forward(
        self, curve: torch.Tensor, features: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Full forward pass (training mode).

        Args:
            curve: Ground-truth stress curve, shape (B, curve_dim).
            features: Input feature tensor, shape (B, n_features).

        Returns:
            Tuple of (reconstructed_curve, mu, log_var).
        """
        condition = self.condition_encoder(features)
        mu, log_var = self.encoder(curve, condition)
        z = self.reparameterize(mu, log_var)
        recon = self.decoder(z, condition)
        return recon, mu, log_var

    def generate(
        self,
        features: torch.Tensor,
        n_samples: int = 1,
    ) -> torch.Tensor:
        """Generate stress-strain curves from input features.

        Args:
            features: Input feature tensor, shape (B, n_features).
            n_samples: Number of stochastic samples per input.

        Returns:
            Generated curves, shape (B, n_samples, curve_dim) if n_samples>1
            else (B, curve_dim).
        """
        self.eval()
        with torch.no_grad():
            condition = self.condition_encoder(features)  # (B, cond_dim)
            B = features.shape[0]

            if n_samples == 1:
                z = torch.randn(B, self.latent_dim, device=features.device)
                return self.decoder(z, condition)
            else:
                samples = []
                for _ in range(n_samples):
                    z = torch.randn(B, self.latent_dim, device=features.device)
                    samples.append(self.decoder(z, condition))
                return torch.stack(samples, dim=1)  # (B, n_samples, curve_dim)

    def save(self, path: Path) -> None:
        """Save model state dict.

        Args:
            path: Destination .pt file path.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({"state_dict": self.state_dict()}, path)
        logger.info(f"CVAE saved: {path}")

    @classmethod
    def load(cls, path: Path, **kwargs: int | list[int]) -> "CVAE":
        """Load CVAE from saved state dict.

        Args:
            path: Source .pt file path.
            **kwargs: Constructor arguments.

        Returns:
            Loaded CVAE instance.
        """
        path = Path(path)
        model = cls(**kwargs)
        ckpt = torch.load(path, map_location="cpu", weights_only=True)
        model.load_state_dict(ckpt["state_dict"])
        model.eval()
        logger.info(f"CVAE loaded: {path}")
        return model
