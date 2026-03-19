"""FT-Transformer (Feature Tokenizer + Transformer) for tabular regression.

Based on: Gorishniy et al. (2021) "Revisiting Deep Learning Models for Tabular Data"
with modern PyTorch 2.x enhancements.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from utils.logging import get_logger

logger = get_logger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Building Blocks
# ──────────────────────────────────────────────────────────────────────────────


class FeatureTokenizer(nn.Module):
    """Embeds numeric features into a shared d_token dimensional space.

    Each feature gets its own linear projection W_i such that
    x_i → W_i * x_i + b_i, producing a token per feature.
    """

    def __init__(self, n_features: int, d_token: int) -> None:
        super().__init__()
        self.weight = nn.Parameter(torch.empty(n_features, d_token))
        self.bias = nn.Parameter(torch.zeros(n_features, d_token))
        nn.init.kaiming_uniform_(self.weight, a=math.sqrt(5))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Tokenize input features.

        Args:
            x: Input tensor of shape (B, n_features).

        Returns:
            Token tensor of shape (B, n_features, d_token).
        """
        return x.unsqueeze(-1) * self.weight.unsqueeze(0) + self.bias.unsqueeze(0)


class ReGLU(nn.Module):
    """Rectified Gated Linear Unit activation."""

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        a, b = x.chunk(2, dim=-1)
        return a * F.relu(b)


class FeedForward(nn.Module):
    """Transformer FFN with ReGLU or GELU activation."""

    def __init__(
        self,
        d_token: int,
        d_hidden: int,
        dropout: float = 0.0,
        activation: str = "reglu",
    ) -> None:
        super().__init__()
        out_mult = 2 if activation == "reglu" else 1
        self.linear1 = nn.Linear(d_token, d_hidden * out_mult)
        self.linear2 = nn.Linear(d_hidden, d_token)
        self.dropout = nn.Dropout(dropout)
        self.activation = ReGLU() if activation == "reglu" else nn.GELU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.linear2(self.dropout(self.activation(self.linear1(x))))


class MultiheadAttention(nn.Module):
    """Standard multi-head attention with optional dropout."""

    def __init__(self, d_token: int, n_heads: int, dropout: float = 0.0) -> None:
        super().__init__()
        assert d_token % n_heads == 0
        self.attn = nn.MultiheadAttention(
            embed_dim=d_token,
            num_heads=n_heads,
            dropout=dropout,
            batch_first=True,
        )
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.attn(x, x, x)
        return self.dropout(out)


class TransformerBlock(nn.Module):
    """Single Transformer block with pre-normalization."""

    def __init__(
        self,
        d_token: int,
        n_heads: int,
        ffn_d_hidden: int,
        attn_dropout: float = 0.2,
        ffn_dropout: float = 0.1,
        residual_dropout: float = 0.0,
        activation: str = "reglu",
    ) -> None:
        super().__init__()
        self.norm1 = nn.LayerNorm(d_token)
        self.norm2 = nn.LayerNorm(d_token)
        self.attn = MultiheadAttention(d_token, n_heads, attn_dropout)
        self.ffn = FeedForward(d_token, ffn_d_hidden, ffn_dropout, activation)
        self.res_drop = nn.Dropout(residual_dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.res_drop(self.attn(self.norm1(x)))
        x = x + self.res_drop(self.ffn(self.norm2(x)))
        return x


# ──────────────────────────────────────────────────────────────────────────────
# Main FT-Transformer
# ──────────────────────────────────────────────────────────────────────────────


class FTTransformer(nn.Module):
    """FT-Transformer for tabular regression.

    Inputs numeric features via per-feature tokenization, applies a stack of
    Transformer blocks, then pools the [CLS] token to predict scalar properties.

    Attributes:
        tokenizer: FeatureTokenizer module.
        cls_token: Learnable CLS token.
        blocks: Stack of TransformerBlocks.
        head: Final prediction head.
    """

    def __init__(
        self,
        n_features: int,
        n_targets: int,
        d_token: int = 192,
        n_blocks: int = 3,
        attention_n_heads: int = 8,
        attention_dropout: float = 0.2,
        ffn_d_hidden: int = 256,
        ffn_dropout: float = 0.1,
        residual_dropout: float = 0.0,
        activation: str = "reglu",
    ) -> None:
        """Initialize FT-Transformer.

        Args:
            n_features: Number of input features.
            n_targets: Number of output scalar targets.
            d_token: Token embedding dimension.
            n_blocks: Number of Transformer blocks.
            attention_n_heads: Number of attention heads.
            attention_dropout: Attention weight dropout.
            ffn_d_hidden: FFN hidden dimension.
            ffn_dropout: FFN activation dropout.
            residual_dropout: Residual connection dropout.
            activation: FFN activation ('reglu' or 'gelu').
        """
        super().__init__()
        self.tokenizer = FeatureTokenizer(n_features, d_token)
        self.cls_token = nn.Parameter(torch.zeros(1, 1, d_token))
        nn.init.normal_(self.cls_token, std=0.02)

        self.blocks = nn.ModuleList(
            [
                TransformerBlock(
                    d_token=d_token,
                    n_heads=attention_n_heads,
                    ffn_d_hidden=ffn_d_hidden,
                    attn_dropout=attention_dropout,
                    ffn_dropout=ffn_dropout,
                    residual_dropout=residual_dropout,
                    activation=activation,
                )
                for _ in range(n_blocks)
            ]
        )

        self.norm = nn.LayerNorm(d_token)
        self.head = nn.Sequential(
            nn.Linear(d_token, d_token // 2),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(d_token // 2, n_targets),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Args:
            x: Input features, shape (B, n_features).

        Returns:
            Predictions, shape (B, n_targets).
        """
        B = x.shape[0]
        tokens = self.tokenizer(x)  # (B, n_features, d_token)
        cls = self.cls_token.expand(B, -1, -1)  # (B, 1, d_token)
        tokens = torch.cat([cls, tokens], dim=1)  # (B, n_features+1, d_token)

        for block in self.blocks:
            tokens = block(tokens)

        cls_out = self.norm(tokens[:, 0])  # (B, d_token)
        return self.head(cls_out)  # (B, n_targets)

    def save(self, path: Path) -> None:
        """Save model state dict and architecture config.

        Args:
            path: Destination .pt file path.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({"state_dict": self.state_dict()}, path)
        logger.info(f"FT-Transformer saved: {path}")

    @classmethod
    def load(cls, path: Path, **kwargs: int | float | str | bool) -> "FTTransformer":
        """Load FT-Transformer from saved state dict.

        Args:
            path: Source .pt file path.
            **kwargs: Constructor arguments (same as __init__).

        Returns:
            Loaded FTTransformer instance.
        """
        path = Path(path)
        model = cls(**kwargs)
        ckpt = torch.load(path, map_location="cpu", weights_only=True)
        model.load_state_dict(ckpt["state_dict"])
        model.eval()
        logger.info(f"FT-Transformer loaded: {path}")
        return model
