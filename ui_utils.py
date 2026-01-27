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
    try:
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    except:
        pass

# ============================================
# ALIASES EM PORTUGUÊS (para padronização)
# ============================================

criar_embed = create_embed
criar_embed_sucesso = create_success_embed
criar_embed_erro = create_error_embed
criar_embed_aviso = create_warning_embed
criar_embed_info = create_info_embed

# ============================================
# BASE UI COMPONENTS
# ============================================

class BaseMenuView(View):
    """
    Base View class enforcing:
    1. Interaction check (only author can use)
    2. Timeout handling (disable items)
    3. Error handling
    """
    def __init__(self, *, user_id: int, timeout: int = 180):
        super().__init__(timeout=timeout)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                f"{EMOJI_ERROR} Apenas quem abriu este menu pode interagir.",
                ephemeral=True
            )
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        # Note: We can't edit the message easily without reference, 
        # so we rely on the user trying to click and failing, 
        # or we pass message ref in future if needed.

    async def on_error(self, interaction: discord.Interaction, error: Exception, item):
        await handle_interaction_error(interaction, error)

# ============================================
# GENERIC VIEWS
# ============================================

class ConfirmView(BaseMenuView):
    """Generic confirmation view."""
    def __init__(self, user_id: int, confirm_label="Confirmar", cancel_label="Cancelar"):
        super().__init__(user_id=user_id, timeout=60)
        self.value = None

    @discord.ui.button(label="Confirmar", style=discord.ButtonStyle.green, emoji=EMOJI_SUCCESS)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()
        await interaction.response.defer() # Acknowledge

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.red, emoji=EMOJI_ERROR)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        await interaction.response.defer() # Acknowledge

