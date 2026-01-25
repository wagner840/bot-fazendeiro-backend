"""
UI Utilities for Bot Fazendeiro.
Standardized embeds, colors, and common UI components.
"""
import discord
from discord.ui import View, Button, Select

# ============================================
# COLORS
# ============================================
COLOR_SUCCESS = 0x2ecc71  # Emerald Green
COLOR_WARNING = 0xf1c40f  # Sunflower Yellow
COLOR_ERROR = 0xe74c3c    # Alizarin Red
COLOR_INFO = 0x3498db     # Peter River Blue
COLOR_NEUTRAL = 0x95a5a6  # Concrete Gray

# ============================================
# EMOJIS
# ============================================
EMOJI_SUCCESS = "✅"
EMOJI_WARNING = "⚠️"
EMOJI_ERROR = "❌"
EMOJI_INFO = "ℹ️"
EMOJI_LOADING = "⏳"

# ============================================
# FACTORY FUNCTIONS
# ============================================

def create_embed(title: str, description: str, color: int, emoji: str = "") -> discord.Embed:
    """Generic embed factory."""
    if emoji:
        title = f"{emoji} {title}"
    return discord.Embed(title=title, description=description, color=color)

def create_success_embed(title: str = "Success", description: str = "") -> discord.Embed:
    """Creates a standardized success embed."""
    return create_embed(title, description, COLOR_SUCCESS, EMOJI_SUCCESS)

def create_error_embed(title: str = "Error", description: str = "") -> discord.Embed:
    """Creates a standardized error embed."""
    return create_embed(title, description, COLOR_ERROR, EMOJI_ERROR)

def create_warning_embed(title: str = "Warning", description: str = "") -> discord.Embed:
    """Creates a standardized warning embed."""
    return create_embed(title, description, COLOR_WARNING, EMOJI_WARNING)

def create_info_embed(title: str = "Info", description: str = "") -> discord.Embed:
    """Creates a standardized info embed."""
    return create_embed(title, description, COLOR_INFO, EMOJI_INFO)

# ============================================
# INTERACTION HELPER
# ============================================

async def handle_interaction_error(interaction: discord.Interaction, error: Exception):
    """Global handler for interaction errors."""
    embed = create_error_embed(
        title="Ocorreu um erro",
        description=f"Algo deu errado ao processar sua solicitação.\n`{str(error)}`"
    )
    if interaction.response.is_done():
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=True)
